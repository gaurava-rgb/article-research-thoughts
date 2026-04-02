"""
ingestion/readwise.py — Readwise Reader API client

Fetches all articles from the Readwise Reader API using paginated requests,
then stores new articles into the Supabase `sources` table.

Usage:
    from second_brain.ingestion.readwise import fetch_all_articles, store_articles

    articles = fetch_all_articles(cfg.readwise.token)
    new_count, skipped_count = store_articles(articles, db)

Readwise Reader API v3 overview:
    GET https://readwise.io/api/v3/list/
    Headers: Authorization: Token {READWISE_TOKEN}
    Optional query param: ?pageCursor={cursor}
    Response: { "count": N, "nextPageCursor": "..." | null, "results": [...] }
    Pagination: keep fetching with nextPageCursor until it is null.

Why httpx.Client (synchronous)?
    The CLI is synchronous; no event loop is running. httpx.Client is
    simpler than asyncio here. The timeout=30 prevents infinite hangs on
    slow network.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Optional

import httpx
import supabase
import tiktoken

if TYPE_CHECKING:
    from second_brain.providers.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


# =============================================================================
# Data model
# =============================================================================

@dataclass
class ReadwiseArticle:
    """
    Represents one article fetched from the Readwise Reader API.

    All fields except `text` can be None — Readwise allows sparse article
    metadata (e.g., highlights with no URL, or no author set).
    """
    readwise_id: str            # Readwise's own unique article ID
    title: str                  # Article title
    author: Optional[str]       # Author name (may be None)
    url: Optional[str]          # Source URL (may be None for highlights)
    published_at: Optional[str] # ISO date string from the API (e.g. "2024-01-15")
    text: str                   # Plain text content — used for chunking
    ingested_at: str            # ISO timestamp set at fetch time (UTC)


# =============================================================================
# API client
# =============================================================================

READWISE_API_URL = "https://readwise.io/api/v3/list/"

# Minimum text length to keep an article. Articles with very short text
# (e.g. highlights with no body) are not useful for semantic search.
MIN_TEXT_LENGTH = 50

# Source-level embeddings operate on whole articles, so cap them to a safe token
# budget for text-embedding-3-small compatible providers.
MAX_SOURCE_EMBEDDING_TOKENS = 8000
_ENCODING_NAME = "cl100k_base"


class _HTMLToTextParser(HTMLParser):
    """Convert Reader HTML content into rough plain text for embeddings/chunking."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(" ".join(self._parts).split())


def _extract_text_from_html(html_content: str | None) -> str:
    """Return readable plain text from Reader's html_content field."""
    if not html_content:
        return ""

    parser = _HTMLToTextParser()
    parser.feed(html_content)
    parser.close()
    return parser.get_text()


def _extract_article_text(result: dict) -> tuple[str, str]:
    """Prefer plain content, then fall back to html_content text extraction."""
    plain_text = (result.get("content") or "").strip()
    if plain_text:
        return plain_text, "content"

    html_text = _extract_text_from_html(result.get("html_content"))
    if html_text:
        return html_text, "html_content"

    return "", "missing"


def _truncate_for_source_embedding(text: str, max_tokens: int = MAX_SOURCE_EMBEDDING_TOKENS) -> tuple[str, bool]:
    """Trim overly long whole-source text to a safe embedding token limit."""
    enc = tiktoken.get_encoding(_ENCODING_NAME)
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text, False
    return enc.decode(tokens[:max_tokens]), True


def _embed_source_text(
    text: str,
    readwise_id: str,
    embed_provider: "EmbeddingProvider",
) -> list[float]:
    """Embed whole-source text using the same truncation policy as normal sync."""
    source_text, was_truncated = _truncate_for_source_embedding(text)
    if was_truncated:
        logger.info(
            "Truncated source embedding input for %s to %s tokens",
            readwise_id,
            MAX_SOURCE_EMBEDDING_TOKENS,
        )
    return embed_provider.embed([source_text])[0]


def _is_duplicate_readwise_id_error(exc: Exception) -> bool:
    """Detect duplicate-key insert failures for the sources.readwise_id unique constraint."""
    message = str(exc)
    return (
        "sources_readwise_id_key" in message
        or ('"code": "23505"' in message)
        or ("'code': '23505'" in message)
    )


def fetch_all_articles(token: str, updated_after: Optional[str] = None) -> list[ReadwiseArticle]:
    """
    Fetch articles from the Readwise Reader API using paginated requests.

    Incremental sync:
        Pass `updated_after` as an ISO 8601 timestamp (e.g. "2026-03-23T00:00:00Z")
        to only fetch articles added or modified since that time. On a first run
        (empty DB), omit it to fetch the full corpus.

        The caller should query MAX(ingested_at) from the sources table and pass
        it here — this reduces API calls from ~38 down to 1-2 on typical runs.

    Pagination note:
        The API uses `pageCursor` query parameters. Each response includes a
        `nextPageCursor` field. We pass it on the next request. When
        `nextPageCursor` is null, we have fetched all pages.

        History: A prior bug in this codebase used offset-based pagination
        which could miss articles when the cursor drifted. pageCursor is the
        correct approach — it is a stable opaque token.

    Args:
        token: Readwise API token (from READWISE_TOKEN environment variable).
        updated_after: Optional ISO 8601 timestamp. Only articles updated after
            this time are returned. If None, all articles are fetched.

    Returns:
        List of ReadwiseArticle dataclasses. Articles with fewer than
        MIN_TEXT_LENGTH characters of text are filtered out.

    Raises:
        RuntimeError: If the API returns a non-200 HTTP status.
    """
    articles: list[ReadwiseArticle] = []
    page_cursor: Optional[str] = None
    page_num = 0
    raw_total = 0
    filtered_short_total = 0
    html_fallback_total = 0

    if updated_after:
        logger.info("Incremental sync: fetching articles updated after %s", updated_after)
    else:
        logger.info("Full sync: fetching all articles (no updatedAfter filter)")

    # Use a synchronous httpx client — the CLI has no async event loop.
    with httpx.Client(timeout=30) as client:
        while True:
            page_num += 1

            # Ask Reader for html_content so we can recover text when `content`
            # is null for newer saved documents.
            params: dict = {"withHtmlContent": "true"}
            if updated_after is not None:
                params["updatedAfter"] = updated_after
            if page_cursor is not None:
                params["pageCursor"] = page_cursor

            response = client.get(
                READWISE_API_URL,
                headers={"Authorization": f"Token {token}"},
                params=params,
            )

            # Raise on any non-200 response with a descriptive error
            if response.status_code != 200:
                raise RuntimeError(
                    f"Readwise API error {response.status_code}: {response.text}"
                )

            data = response.json()
            results = data.get("results", [])
            raw_total += len(results)
            page_kept = 0
            page_filtered_short = 0
            page_html_fallback = 0

            # Map each raw dict to a ReadwiseArticle dataclass
            ingested_at = datetime.datetime.utcnow().isoformat() + "Z"
            for result in results:
                text, text_source = _extract_article_text(result)

                # Skip articles with insufficient text — not useful for search
                if len(text.strip()) < MIN_TEXT_LENGTH:
                    filtered_short_total += 1
                    page_filtered_short += 1
                    continue

                if text_source == "html_content":
                    html_fallback_total += 1
                    page_html_fallback += 1

                articles.append(ReadwiseArticle(
                    readwise_id=result["id"],
                    title=result.get("title") or "",
                    author=result.get("author"),
                    # source_url is the original content URL (x.com, substack, etc.)
                    # url is the Readwise Reader wrapper — not useful for citation
                    url=result.get("source_url") or result.get("url"),
                    published_at=result.get("published_date"),
                    text=text,
                    ingested_at=ingested_at,
                ))
                page_kept += 1

            print(f"Fetched page {page_num}, total so far: {len(articles)}")
            logger.info(
                "Readwise page %s: %s raw, %s kept, %s filtered_short, %s html_fallback, total kept=%s",
                page_num,
                len(results),
                page_kept,
                page_filtered_short,
                page_html_fallback,
                len(articles),
            )

            # Advance cursor — if None, we've reached the last page
            page_cursor = data.get("nextPageCursor")
            if page_cursor is None:
                break

    logger.info(
        "Readwise fetch complete: %s raw, %s kept, %s filtered_short, %s html_fallback",
        raw_total,
        len(articles),
        filtered_short_total,
        html_fallback_total,
    )
    return articles


# =============================================================================
# Incremental sync helper
# =============================================================================

def get_last_ingested_at(db: "supabase.Client") -> Optional[str]:
    """
    Return the most recent `ingested_at` timestamp from the sources table.

    Used to drive incremental Readwise syncs via the `updatedAfter` API param.
    Returns None if the sources table is empty (first run → full fetch).
    """
    result = db.table("sources").select("ingested_at").order("ingested_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]["ingested_at"]
    return None


# =============================================================================
# Database storage
# =============================================================================

def store_articles(
    articles: list[ReadwiseArticle],
    db: supabase.Client,
    embed_provider: "EmbeddingProvider | None" = None,
) -> tuple[int, int]:
    """
    Store new articles into the Supabase `sources` table.

    Deduplication strategy:
        Before inserting, we check whether a row with the same `readwise_id`
        already exists. If it does, we skip it. This makes the sync command
        idempotent — re-running it will not create duplicate rows.

    Args:
        articles: List of ReadwiseArticle instances to persist.
        db:             Supabase client (from second_brain.db.get_db_client()).
        embed_provider: Optional embedding provider used to store one
                        source-level embedding per newly inserted article.

    Returns:
        Tuple of (new_count, skipped_count, new_source_ids).
        - new_count:      Number of articles inserted.
        - skipped_count:  Number of articles already in the DB (skipped).
        - new_source_ids: UUIDs of the newly inserted sources (for chunking).
    """
    new_count = 0
    skipped_count = 0
    new_source_ids: list[str] = []

    for article in articles:
        # Check if this article already exists in sources by readwise_id.
        # Using .eq() for an exact match on the unique Readwise identifier.
        existing = (
            db.table("sources")
            .select("id")
            .eq("readwise_id", article.readwise_id)
            .execute()
        )

        if existing.data:
            # Article already stored — skip to avoid duplicates
            skipped_count += 1
            continue

        # Store one source-level embedding per new article so future topic work
        # can operate on whole sources without disturbing chunk retrieval.
        source_embedding = None
        if embed_provider is not None:
            source_embedding = _embed_source_text(
                article.text,
                article.readwise_id,
                embed_provider,
            )

        # Insert the new article into sources.
        # Supabase accepts ISO date strings directly for timestamp/date columns.
        try:
            result = db.table("sources").insert({
                "title": article.title,
                "author": article.author,
                "url": article.url,
                "published_at": article.published_at,
                "ingested_at": article.ingested_at,
                "readwise_id": article.readwise_id,
                "raw_text": article.text,
                "source_embedding": source_embedding,
            }).execute()
            if result.data:
                new_source_ids.append(result.data[0]["id"])
        except Exception as exc:
            if _is_duplicate_readwise_id_error(exc):
                logger.info(
                    "Readwise source %s already inserted by another sync pass; skipping duplicate",
                    article.readwise_id,
                )
                skipped_count += 1
                continue
            raise

        new_count += 1

    return new_count, skipped_count, new_source_ids


def backfill_missing_source_embeddings(
    db: supabase.Client,
    embed_provider: "EmbeddingProvider",
    limit: int | None = None,
) -> tuple[int, int, int]:
    """
    Fill NULL `sources.source_embedding` values for older rows.

    Reuses the same whole-source embedding assumptions as the normal insert path:
    embed `raw_text`, truncate to the safe source token budget, and only touch rows
    that are currently missing a source-level vector.

    Returns:
        Tuple of (missing_count, updated_count, skipped_no_text_count).
    """
    result = db.table("sources").select(
        "id, readwise_id, raw_text, source_embedding"
    ).execute()
    missing_rows = [
        row for row in result.data
        if row.get("source_embedding") is None
    ]
    if limit is not None:
        missing_rows = missing_rows[:limit]

    updated_count = 0
    skipped_no_text_count = 0

    for row in missing_rows:
        raw_text = (row.get("raw_text") or "").strip()
        if not raw_text:
            logger.warning(
                "Skipping source embedding backfill for %s because raw_text is empty",
                row.get("readwise_id") or row["id"],
            )
            skipped_no_text_count += 1
            continue

        source_embedding = _embed_source_text(
            raw_text,
            row.get("readwise_id") or row["id"],
            embed_provider,
        )
        (
            db.table("sources")
            .update({"source_embedding": source_embedding})
            .eq("id", row["id"])
            .execute()
        )
        updated_count += 1

    return len(missing_rows), updated_count, skipped_no_text_count


def chunk_new_sources(
    source_ids: list[str],
    db: "supabase.Client",
    embed_provider: "EmbeddingProvider",
    *,
    target_tokens: int,
    overlap_tokens: int,
) -> int:
    """
    Chunk and embed a specific list of newly inserted source IDs.

    Called by the sync flow immediately after store_articles() — only processes
    the articles that were just inserted, not the whole corpus.

    Returns total number of chunks created.
    """
    from second_brain.ingestion.chunker import chunk_text, store_chunks_with_embeddings

    total_chunks = 0
    for source_id in source_ids:
        row = db.table("sources").select("id, readwise_id, raw_text").eq("id", source_id).execute().data
        if not row:
            continue
        row = row[0]
        raw_text = (row.get("raw_text") or "").strip()
        if not raw_text:
            logger.warning("Skipping chunk creation for %s — no raw_text", source_id)
            continue
        chunks = chunk_text(raw_text, source_id=source_id, target_tokens=target_tokens, overlap_tokens=overlap_tokens)
        if chunks:
            stored = store_chunks_with_embeddings(chunks, embed_provider, db)
            total_chunks += stored
            logger.info("Chunked source %s → %s chunks", source_id, stored)

    return total_chunks


def backfill_missing_chunks(
    db: supabase.Client,
    embed_provider: "EmbeddingProvider",
    *,
    target_tokens: int,
    overlap_tokens: int,
) -> tuple[int, int, int, int]:
    """
    Chunk and embed any stored sources that still have zero chunk rows.

    This is a repair/backfill command — use `chunk_new_sources()` for normal sync.
    It repairs partial-progress ingestion runs where a source row exists but the
    chunking step never completed. It is intentionally source-agnostic: if a row in
    `sources` has `raw_text` and no related `chunks`, it is a repair candidate.

    Returns:
        Tuple of (missing_count, repaired_source_count, total_chunks, skipped_no_text_count).
    """
    from second_brain.ingestion.chunker import chunk_text, store_chunks_with_embeddings

    all_sources = db.table("sources").select("id, readwise_id, title, raw_text").execute().data
    # Fetch ALL chunk source_ids with pagination — Supabase caps at 1000 rows per
    # request, so without pagination we'd miss chunks and re-process already-chunked
    # sources, creating massive duplicates.
    chunked_ids: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        page = db.table("chunks").select("source_id").range(offset, offset + page_size - 1).execute().data
        for row in page:
            chunked_ids.add(row["source_id"])
        if len(page) < page_size:
            break
        offset += page_size
    missing_rows = [row for row in all_sources if row["id"] not in chunked_ids]

    repaired_source_count = 0
    total_chunks = 0
    skipped_no_text_count = 0

    for row in missing_rows:
        raw_text = (row.get("raw_text") or "").strip()
        if not raw_text:
            logger.warning(
                "Skipping chunk backfill for %s because raw_text is empty",
                row.get("readwise_id") or row["id"],
            )
            skipped_no_text_count += 1
            continue

        chunks = chunk_text(
            raw_text,
            source_id=str(row["id"]),
            target_tokens=target_tokens,
            overlap_tokens=overlap_tokens,
        )
        if not chunks:
            logger.info(
                "Skipping chunk backfill for %s because chunking produced no usable chunks",
                row.get("readwise_id") or row["id"],
            )
            continue

        try:
            stored = store_chunks_with_embeddings(chunks, embed_provider, db)
        except Exception as exc:
            logger.warning(
                "Skipping chunk backfill for %s — embedding failed: %s",
                row.get("readwise_id") or row["id"],
                exc,
            )
            skipped_no_text_count += 1
            continue
        if stored > 0:
            repaired_source_count += 1
            total_chunks += stored

    return len(missing_rows), repaired_source_count, total_chunks, skipped_no_text_count

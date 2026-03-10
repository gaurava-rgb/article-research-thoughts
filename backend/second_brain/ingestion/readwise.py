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
from dataclasses import dataclass
from typing import Optional

import httpx
import supabase


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


def fetch_all_articles(token: str) -> list[ReadwiseArticle]:
    """
    Fetch every article from the Readwise Reader API using paginated requests.

    Pagination note:
        The API uses `pageCursor` query parameters. Each response includes a
        `nextPageCursor` field. We pass it on the next request. When
        `nextPageCursor` is null, we have fetched all pages.

        History: A prior bug in this codebase used offset-based pagination
        which could miss articles when the cursor drifted. pageCursor is the
        correct approach — it is a stable opaque token.

    Args:
        token: Readwise API token (from READWISE_TOKEN environment variable).

    Returns:
        List of ReadwiseArticle dataclasses. Articles with fewer than
        MIN_TEXT_LENGTH characters of text are filtered out.

    Raises:
        RuntimeError: If the API returns a non-200 HTTP status.
    """
    articles: list[ReadwiseArticle] = []
    page_cursor: Optional[str] = None
    page_num = 0

    # Use a synchronous httpx client — the CLI has no async event loop.
    with httpx.Client(timeout=30) as client:
        while True:
            page_num += 1

            # Build query params — only include pageCursor after the first request
            params: dict = {}
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

            # Map each raw dict to a ReadwiseArticle dataclass
            ingested_at = datetime.datetime.utcnow().isoformat() + "Z"
            for result in results:
                text = result.get("text") or ""

                # Skip articles with insufficient text — not useful for search
                if len(text.strip()) < MIN_TEXT_LENGTH:
                    continue

                articles.append(ReadwiseArticle(
                    readwise_id=result["id"],
                    title=result.get("title") or "",
                    author=result.get("author"),
                    url=result.get("url"),
                    published_at=result.get("published_date"),
                    text=text,
                    ingested_at=ingested_at,
                ))

            print(f"Fetched page {page_num}, total so far: {len(articles)}")

            # Advance cursor — if None, we've reached the last page
            page_cursor = data.get("nextPageCursor")
            if page_cursor is None:
                break

    return articles


# =============================================================================
# Database storage
# =============================================================================

def store_articles(
    articles: list[ReadwiseArticle],
    db: supabase.Client,
) -> tuple[int, int]:
    """
    Store new articles into the Supabase `sources` table.

    Deduplication strategy:
        Before inserting, we check whether a row with the same `readwise_id`
        already exists. If it does, we skip it. This makes the sync command
        idempotent — re-running it will not create duplicate rows.

    Args:
        articles: List of ReadwiseArticle instances to persist.
        db:       Supabase client (from second_brain.db.get_db_client()).

    Returns:
        Tuple of (new_count, skipped_count).
        - new_count:     Number of articles inserted.
        - skipped_count: Number of articles already in the DB (skipped).
    """
    new_count = 0
    skipped_count = 0

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

        # Insert the new article into sources.
        # Supabase accepts ISO date strings directly for timestamp/date columns.
        db.table("sources").insert({
            "title": article.title,
            "author": article.author,
            "url": article.url,
            "published_at": article.published_at,
            "ingested_at": article.ingested_at,
            "readwise_id": article.readwise_id,
            "raw_text": article.text,
        }).execute()

        new_count += 1

    return new_count, skipped_count

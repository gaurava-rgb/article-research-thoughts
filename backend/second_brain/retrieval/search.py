"""
search.py — Hybrid retrieval engine for Second Brain

Implements hybrid search combining two signals:
  1. Vector similarity  (pgvector cosine distance, weight = 70%)
  2. Full-text search   (PostgreSQL ts_rank, weight = 30%)

The scoring weights (70/30) are a reasonable starting point for a personal
knowledge base. They can be tuned by editing the SQL function `hybrid_search`
in schema.sql — no Python changes needed.

Usage:
    from second_brain.retrieval.search import hybrid_search, SearchResult

    results = hybrid_search("what do I think about AI safety?", top_k=5)
    for r in results:
        print(r.title, r.hybrid_score)

Date filters:
    results = hybrid_search("AI", top_k=5, after="2024-01-01")
    results = hybrid_search("AI", top_k=5, before="2024-12-31")
"""

from __future__ import annotations

from dataclasses import dataclass

# NOTE: get_db_client and get_embedding_provider are imported lazily inside
# hybrid_search() rather than at module level. This keeps the import cheap
# (no env var validation, no network calls) and consistent with the lazy-import
# pattern used in cli.py (established in Plan 02).


# =============================================================================
# SearchResult dataclass — one row returned by hybrid_search
# =============================================================================

@dataclass
class SearchResult:
    """
    Represents a single chunk returned by the hybrid search function.

    Attributes:
        chunk_id:     UUID of the chunk row in the `chunks` table.
        source_id:    UUID of the parent source in the `sources` table.
        content:      The text of the matched chunk (may be up to ~500 tokens).
        vector_score: Cosine similarity score (0–1, higher = more similar).
        fts_score:    PostgreSQL ts_rank score for full-text relevance.
        hybrid_score: Weighted blend — 70% vector_score + 30% fts_score.
        title:        Title of the source article.
        author:       Author of the source article (may be None).
        url:          URL of the source article (may be None).
        published_at: Publication date as an ISO string (may be None).
    """
    chunk_id: str
    source_id: str
    content: str
    vector_score: float
    fts_score: float
    hybrid_score: float
    title: str
    author: str | None
    url: str | None
    published_at: str | None


# =============================================================================
# hybrid_search — main retrieval function
# =============================================================================

def hybrid_search(
    query: str,
    top_k: int = 10,
    after: str | None = None,
    before: str | None = None,
) -> list[SearchResult]:
    """
    Search the knowledge base using a hybrid of vector similarity and FTS.

    Steps:
        1. Embed the query string into a 1536-dimension vector.
        2. Call the `hybrid_search` PostgreSQL function via Supabase RPC.
           The SQL function handles scoring and date filtering entirely in the DB.
        3. Map the returned rows to SearchResult dataclasses.

    The SQL function scores each chunk as:
        hybrid_score = 0.7 * vector_score + 0.3 * fts_score
    Weights are 70/30 (vector-heavy) because semantic meaning is the primary
    retrieval signal in a personal knowledge base. Adjust in schema.sql if needed.

    Args:
        query:  Natural-language question or search phrase.
        top_k:  Maximum number of results to return (default 10).
        after:  ISO date string "YYYY-MM-DD". Only return chunks from sources
                published on or after this date. None = no lower bound.
        before: ISO date string "YYYY-MM-DD". Only return chunks from sources
                published on or before this date. None = no upper bound.

    Returns:
        List of SearchResult sorted by hybrid_score descending. May be empty
        if no chunks match or no data has been ingested.

    Raises:
        RuntimeError: If the Supabase RPC call returns an error.
    """
    # Lazy imports: load config-dependent modules only when search is actually called.
    # This keeps `from second_brain.retrieval.search import SearchResult` fast
    # (no env var validation) while still catching missing env vars at call time.
    from second_brain.db import get_db_client
    from second_brain.providers.embeddings import get_embedding_provider

    # Step 1: Embed the query.
    # embed() accepts a list and returns a list of vectors; we only need the first.
    embedding: list[float] = get_embedding_provider().embed([query])[0]

    # Step 2: Call the hybrid_search SQL function via Supabase RPC.
    # Parameters map directly to the PostgreSQL function signature in schema.sql.
    # after/before are ISO date strings ("YYYY-MM-DD") that the SQL function
    # casts to the `date` type for published_at comparisons.
    db = get_db_client()
    response = db.rpc(
        "hybrid_search",
        {
            "query_embedding": embedding,   # list of floats → Supabase serialises to vector
            "query_text": query,            # raw text for PostgreSQL plainto_tsquery()
            "match_count": top_k,
            "date_after": after,            # "YYYY-MM-DD" string or None
            "date_before": before,          # "YYYY-MM-DD" string or None
        },
    ).execute()

    # Guard: raise on RPC errors rather than silently returning empty results.
    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Search failed: {response.error}")

    # Step 3: Map result rows to SearchResult dataclasses.
    if not response.data:
        return []

    results: list[SearchResult] = []
    for row in response.data:
        results.append(
            SearchResult(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                content=row["content"],
                vector_score=float(row["vector_score"]),
                fts_score=float(row["fts_score"]),
                hybrid_score=float(row["hybrid_score"]),
                title=row["title"],
                author=row.get("author"),
                url=row.get("url"),
                published_at=str(row["published_at"]) if row.get("published_at") else None,
            )
        )

    return results

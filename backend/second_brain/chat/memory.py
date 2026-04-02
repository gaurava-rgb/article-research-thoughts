"""Cross-session conversation similarity (CHAT-04).

Searches past assistant messages semantically to find related prior
conversations. Results are returned as structured data for the UI to
surface as a visible nudge — they are NOT injected into the LLM prompt.

Surfacing (not injecting) keeps source articles as the only retrieval
context for the LLM. Past AI responses are derivatives; feeding them
back creates derivatives-of-derivatives and causes the model to cite
itself instead of the user's actual reading.

get_db_client is imported at module level so tests can patch it via
patch("second_brain.chat.memory.get_db_client").
"""
from __future__ import annotations

from second_brain.db import get_db_client


def get_embedding_provider():
    """Lazy wrapper — defers config loading until first call."""
    from second_brain.providers.embeddings import get_embedding_provider as _get
    return _get()


def retrieve_similar_conversations(
    query: str,
    current_conversation_id: str,
    top_k: int = 3,
    min_similarity: float = 0.6,
) -> list[dict]:
    """Return past conversations similar to `query` as structured data.

    Used by GET /api/conversations/similar to power a UI nudge
    ("you explored this in conversation X"). Never injected into LLM prompts.

    Args:
        query: The current user message.
        current_conversation_id: Exclude this conversation from results.
        top_k: Number of past messages to retrieve.
        min_similarity: Minimum cosine similarity threshold (0–1).

    Returns:
        List of dicts: [{conversation_id, title, date, similarity}, ...]
        Empty list when no similar conversations meet the threshold.
    """
    embedding = get_embedding_provider().embed([query])[0]
    db = get_db_client()

    response = db.rpc("search_past_messages", {
        "query_embedding": embedding,
        "exclude_conversation_id": current_conversation_id,
        "match_count": top_k,
    }).execute()

    if not response.data:
        return []

    results = []
    for row in response.data:
        sim = row.get("similarity", 0)
        if sim < min_similarity:
            continue
        date_str = row["created_at"][:10] if row.get("created_at") else "unknown"
        results.append({
            "conversation_id": str(row["conv_id"]),
            "title": row.get("conv_title") or "Untitled conversation",
            "date": date_str,
            "similarity": round(sim, 3),
        })

    return results

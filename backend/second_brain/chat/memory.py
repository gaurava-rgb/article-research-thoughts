"""Cross-session memory retrieval (CHAT-04).

Searches past assistant messages semantically to find related prior
conversations. Results are injected into the system prompt so the LLM
can reference them ("we discussed this in a March session").

Uses the search_past_messages SQL function added to schema.sql in Phase 2.

get_db_client and get_embedding_provider are imported at module level so
tests can patch them via patch("second_brain.chat.memory.get_db_client").
These imports only load library code — they do NOT connect to any service
until the functions are actually called.
"""
from __future__ import annotations

from second_brain.db import get_db_client


def get_embedding_provider():
    """Lazy wrapper — defers config loading until first call.

    Defined at module level so tests can patch
    'second_brain.chat.memory.get_embedding_provider'.
    The actual import is deferred to avoid triggering config/env-var
    validation at import time (embeddings.py reads cfg at module level).
    """
    from second_brain.providers.embeddings import get_embedding_provider as _get
    return _get()


def retrieve_memory_context(
    query: str,
    current_conversation_id: str,
    top_k: int = 3,
) -> str:
    """Return a formatted memory context string, or '' if no relevant past conversations.

    Args:
        query: The current user message (used as the search query).
        current_conversation_id: Exclude this conversation from results.
        top_k: Number of past messages to retrieve.

    Returns:
        A multi-line string starting with a context header, suitable for
        injection into the system prompt. Empty string when no matches.
    """
    embedding = get_embedding_provider().embed([query])[0]
    db = get_db_client()

    response = db.rpc("search_past_messages", {
        "query_embedding": embedding,
        "exclude_conversation_id": current_conversation_id,
        "match_count": top_k,
    }).execute()

    if not response.data:
        return ""

    lines = ["[PAST CONVERSATIONS — use these to answer 'we discussed...' questions]"]
    for row in response.data:
        date_str = row["created_at"][:10] if row.get("created_at") else "unknown date"
        title = row.get("conv_title") or "Untitled conversation"
        snippet = (row.get("content") or "")[:200]
        lines.append(f"- Conversation '{title}' ({date_str}): {snippet}")

    return "\n".join(lines)

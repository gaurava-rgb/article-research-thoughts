"""Conversation and message CRUD operations.

get_db_client is imported at module level so tests can patch it via
`patch("second_brain.chat.conversation.get_db_client")`. The import
only triggers the supabase library load — it does NOT open a connection
or read env vars until get_db_client() is actually called.
"""
from __future__ import annotations

from second_brain.db import get_db_client


def create_conversation(title: str | None = None) -> dict:
    """Create a new conversation row and return it."""
    db = get_db_client()
    result = db.table("conversations").insert({"title": title}).execute()
    return result.data[0]


def update_title(conversation_id: str, title: str) -> None:
    """Update the title of a conversation (called after auto-title generation)."""
    db = get_db_client()
    db.table("conversations").update({"title": title}).eq("id", conversation_id).execute()


def list_conversations(limit: int = 50) -> list[dict]:
    """Return conversations ordered by most recently updated."""
    db = get_db_client()
    result = (
        db.table("conversations")
        .select("id, title, created_at, updated_at")
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_messages(conversation_id: str) -> list[dict]:
    """Return all messages for a conversation in chronological order."""
    db = get_db_client()
    result = (
        db.table("messages")
        .select("id, role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data


def save_message(conversation_id: str, role: str, content: str) -> dict:
    """Save a message and bump the conversation's updated_at timestamp."""
    db = get_db_client()
    result = db.table("messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
    }).execute()
    db.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).execute()
    return result.data[0]


def save_message_with_embedding(conversation_id: str, role: str, content: str) -> dict:
    """Save an assistant message and store its embedding for cross-session memory."""
    from second_brain.providers.embeddings import get_embedding_provider
    db = get_db_client()
    embedding = get_embedding_provider().embed([content])[0]
    result = db.table("messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "embedding": embedding,
    }).execute()
    db.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).execute()
    return result.data[0]


def build_messages_for_llm(
    system_prompt: str,
    history: list[dict],
    user_message: str,
    memory_context: str,
) -> list[dict]:
    """Build the messages list for the LLM API call.

    Injects memory context into the system prompt, caps history at last 10
    messages to avoid context window overflow (see Research pitfall 6), then
    appends the new user message.
    """
    full_system = system_prompt
    if memory_context:
        full_system = f"{system_prompt}\n\n{memory_context}"

    # Cap at last 10 messages (20 turns) to stay within context window
    recent_history = history[-10:]

    return [
        {"role": "system", "content": full_system},
        *recent_history,
        {"role": "user", "content": user_message},
    ]

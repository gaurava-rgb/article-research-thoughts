"""Tests for conversation CRUD — covers CHAT-01, CHAT-02, CHAT-03."""
import pytest
from unittest.mock import patch, MagicMock


def test_build_messages_injects_history():
    """CHAT-01: build_messages includes prior turns from same conversation."""
    from second_brain.chat.conversation import build_messages_for_llm
    history = [
        {"role": "user", "content": "Tell me about AGI"},
        {"role": "assistant", "content": "AGI refers to..."},
    ]
    result = build_messages_for_llm(
        system_prompt="You are a knowledge assistant.",
        history=history,
        user_message="What are the risks?",
        memory_context="",
    )
    roles = [m["role"] for m in result]
    assert "user" in roles
    assert "assistant" in roles
    # last message is the new user message
    assert result[-1] == {"role": "user", "content": "What are the risks?"}
    # prior history injected
    assert any(m["content"] == "Tell me about AGI" for m in result)


def test_list_conversations_ordered():
    """CHAT-02: list_conversations returns most-recently-updated first."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"id": "aaa", "title": "Latest", "created_at": "2026-03-10", "updated_at": "2026-03-10T12:00:00"},
        {"id": "bbb", "title": "Older", "created_at": "2026-03-09", "updated_at": "2026-03-09T12:00:00"},
    ]
    with patch("second_brain.chat.conversation.get_db_client", return_value=mock_db):
        from second_brain.chat.conversation import list_conversations
        result = list_conversations(limit=50)
    assert result[0]["id"] == "aaa"


def test_get_messages_ordered():
    """CHAT-03: get_messages returns messages in chronological order."""
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": "m1", "role": "user", "content": "Hello", "created_at": "2026-03-10T10:00:00"},
        {"id": "m2", "role": "assistant", "content": "Hi there", "created_at": "2026-03-10T10:00:05"},
    ]
    with patch("second_brain.chat.conversation.get_db_client", return_value=mock_db):
        from second_brain.chat.conversation import get_messages
        result = get_messages("conv-id-123")
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"

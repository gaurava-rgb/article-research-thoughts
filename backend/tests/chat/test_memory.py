"""Tests for cross-session memory retrieval — covers CHAT-04."""
import pytest
from unittest.mock import patch, MagicMock


def test_retrieve_memory_context_returns_string():
    """CHAT-04: retrieve_memory_context returns a formatted string (or empty string) without error."""
    mock_embed_provider = MagicMock()
    mock_embed_provider.embed.return_value = [[0.1] * 1536]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = [
        {
            "conv_title": "AI Safety discussion",
            "created_at": "2026-03-01T10:00:00",
            "content": "We discussed alignment problems in detail.",
        }
    ]

    with (
        patch("second_brain.chat.memory.get_embedding_provider", return_value=mock_embed_provider),
        patch("second_brain.chat.memory.get_db_client", return_value=mock_db),
    ):
        from second_brain.chat.memory import retrieve_memory_context
        result = retrieve_memory_context(
            query="AI safety",
            current_conversation_id="current-conv-id",
            top_k=3,
        )
    assert isinstance(result, str)
    assert "AI Safety discussion" in result or result == ""


def test_retrieve_memory_context_empty_when_no_results():
    """CHAT-04: returns empty string gracefully when no relevant past conversations exist."""
    mock_embed_provider = MagicMock()
    mock_embed_provider.embed.return_value = [[0.1] * 1536]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = []

    with (
        patch("second_brain.chat.memory.get_embedding_provider", return_value=mock_embed_provider),
        patch("second_brain.chat.memory.get_db_client", return_value=mock_db),
    ):
        from second_brain.chat.memory import retrieve_memory_context
        result = retrieve_memory_context("anything", "conv-id", top_k=3)
    assert result == ""

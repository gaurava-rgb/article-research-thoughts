"""Tests for cross-session conversation similarity — covers CHAT-04."""
from unittest.mock import patch, MagicMock


def test_retrieve_similar_conversations_returns_list():
    """CHAT-04: retrieve_similar_conversations returns a list of dicts (or empty list)."""
    mock_embed_provider = MagicMock()
    mock_embed_provider.embed.return_value = [[0.1] * 1536]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = [
        {
            "conv_id": "conv-abc",
            "conv_title": "AI Safety discussion",
            "created_at": "2026-03-01T10:00:00",
            "content": "We discussed alignment problems in detail.",
            "similarity": 0.85,
        }
    ]

    with (
        patch("second_brain.chat.memory.get_embedding_provider", return_value=mock_embed_provider),
        patch("second_brain.chat.memory.get_db_client", return_value=mock_db),
    ):
        from second_brain.chat.memory import retrieve_similar_conversations
        result = retrieve_similar_conversations(
            query="AI safety",
            current_conversation_id="current-conv-id",
            top_k=3,
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["conversation_id"] == "conv-abc"
    assert result[0]["title"] == "AI Safety discussion"
    assert result[0]["date"] == "2026-03-01"


def test_retrieve_similar_conversations_empty_when_no_results():
    """CHAT-04: returns empty list gracefully when no relevant past conversations exist."""
    mock_embed_provider = MagicMock()
    mock_embed_provider.embed.return_value = [[0.1] * 1536]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = []

    with (
        patch("second_brain.chat.memory.get_embedding_provider", return_value=mock_embed_provider),
        patch("second_brain.chat.memory.get_db_client", return_value=mock_db),
    ):
        from second_brain.chat.memory import retrieve_similar_conversations
        result = retrieve_similar_conversations("anything", "conv-id", top_k=3)

    assert result == []


def test_retrieve_similar_conversations_filters_low_similarity():
    """CHAT-04: results below min_similarity threshold are excluded."""
    mock_embed_provider = MagicMock()
    mock_embed_provider.embed.return_value = [[0.1] * 1536]

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value.data = [
        {
            "conv_id": "conv-low",
            "conv_title": "Tangentially related",
            "created_at": "2026-03-01T10:00:00",
            "content": "Something vaguely related.",
            "similarity": 0.3,  # Below default threshold of 0.6
        }
    ]

    with (
        patch("second_brain.chat.memory.get_embedding_provider", return_value=mock_embed_provider),
        patch("second_brain.chat.memory.get_db_client", return_value=mock_db),
    ):
        from second_brain.chat.memory import retrieve_similar_conversations
        result = retrieve_similar_conversations("AI safety", "conv-id")

    assert result == []

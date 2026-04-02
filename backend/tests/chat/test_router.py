"""Integration tests for the chat API router."""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def test_chat_endpoint_returns_complete_json_response():
    """POST /api/chat should return the current JSON response shape."""
    from api.index import app

    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Grounded answer"))]
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_completion))
        )
    )

    with (
        patch("second_brain.retrieval.search.hybrid_search", return_value=[]),
        patch("second_brain.chat.conversation.get_db_client"),
        patch("second_brain.chat.conversation.get_messages", return_value=[]),
        patch("second_brain.chat.conversation.save_message"),
        patch(
            "second_brain.chat.conversation.build_messages_for_llm",
            return_value=[{"role": "user", "content": "What is AGI?"}],
        ),
        patch(
            "second_brain.config.cfg",
            SimpleNamespace(
                llm=SimpleNamespace(
                    base_url="https://example.com",
                    api_key="test-key",
                    model="test-model",
                )
            ),
        ),
        patch("openai.AsyncOpenAI", return_value=fake_client),
    ):
        client = TestClient(app, raise_server_exceptions=False)

        with patch("second_brain.chat.conversation.get_db_client") as mock_db:
            mock_db.return_value.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "test-conv-id", "title": None, "created_at": "2026-03-10", "updated_at": "2026-03-10"}
            ]
            conv_resp = client.post("/api/conversations")
        conv_id = conv_resp.json()["id"]

        response = client.post(
            "/api/chat",
            json={"conversation_id": conv_id, "message": "What is AGI?"},
        )

    assert response.status_code == 200
    assert response.json() == {"content": "Grounded answer", "sources": []}


class _FakeSyncTable:
    def __init__(self, data):
        self._data = data

    def select(self, _columns: str):
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _FakeSyncDB:
    def table(self, name: str):
        if name == "sources":
            return _FakeSyncTable([])
        if name == "chunks":
            return _FakeSyncTable([])
        raise AssertionError(f"Unexpected table: {name}")


def test_sync_endpoint_passes_embedding_provider_to_store_articles():
    """UI sync should store source embeddings the same way the CLI sync does."""
    from api.index import app

    embed_provider = MagicMock(name="embed_provider")
    db = _FakeSyncDB()

    with (
        patch(
            "second_brain.ingestion.readwise.get_last_ingested_at",
            return_value=None,
        ),
        patch(
            "second_brain.ingestion.readwise.fetch_all_articles",
            return_value=["article-1"],
        ),
        patch(
            "second_brain.ingestion.readwise.store_articles",
            return_value=(1, 0, []),
        ) as mock_store_articles,
        patch("second_brain.db.get_db_client", return_value=db),
        patch(
            "second_brain.providers.embeddings.get_embedding_provider",
            return_value=embed_provider,
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/sync")

    assert response.status_code == 200
    assert response.json()["status"] == "complete"
    mock_store_articles.assert_called_once_with(
        ["article-1"],
        db,
        embed_provider=embed_provider,
    )

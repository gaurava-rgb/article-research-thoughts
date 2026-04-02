"""Integration tests for the chat API router."""
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

TEST_ENV = {
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_KEY": "test-supabase-key",
    "READWISE_TOKEN": "test-readwise-token",
}

import second_brain
import second_brain.providers

fake_config_module = types.ModuleType("second_brain.config")
fake_config_module.cfg = SimpleNamespace(
    llm=SimpleNamespace(
        base_url="https://example.com",
        api_key="test-key",
        model="test-model",
    ),
    readwise=SimpleNamespace(token="test-readwise-token"),
    chunking=SimpleNamespace(target_tokens=500, overlap_tokens=50),
)
sys.modules["second_brain.config"] = fake_config_module
setattr(second_brain, "config", fake_config_module)

fake_embeddings_module = types.ModuleType("second_brain.providers.embeddings")
fake_embeddings_module.get_embedding_provider = MagicMock(name="get_embedding_provider")
sys.modules["second_brain.providers.embeddings"] = fake_embeddings_module
setattr(second_brain.providers, "embeddings", fake_embeddings_module)

fake_llm_module = types.ModuleType("second_brain.providers.llm")
fake_llm_module.get_llm_provider = MagicMock(name="get_llm_provider")
sys.modules["second_brain.providers.llm"] = fake_llm_module
setattr(second_brain.providers, "llm", fake_llm_module)


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
        patch.dict(os.environ, TEST_ENV, clear=False),
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


def test_chat_endpoint_includes_source_classification_fields():
    """POST /api/chat should surface source metadata without breaking the response shape."""
    from api.index import app
    from second_brain.retrieval.search import SearchResult

    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Grounded answer"))]
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_completion))
        )
    )
    source_lookup = MagicMock()
    source_lookup.select.return_value.in_.return_value.execute.return_value.data = []

    with (
        patch.dict(os.environ, TEST_ENV, clear=False),
        patch(
            "second_brain.retrieval.search.hybrid_search",
            return_value=[
                SearchResult(
                    chunk_id="chunk-1",
                    source_id="source-1",
                    content="Relevant passage",
                    vector_score=0.9,
                    fts_score=0.4,
                    hybrid_score=0.75,
                    title="Structured Source",
                    author="Author",
                    url="https://example.com/structured-source",
                    published_at="2026-03-23T00:00:00+00:00",
                    kind="article",
                    tier="analysis",
                    publisher="Example.com",
                )
            ],
        ),
        patch("second_brain.chat.conversation.get_db_client"),
        patch("second_brain.chat.conversation.get_messages", return_value=[]),
        patch("second_brain.chat.conversation.save_message"),
        patch(
            "second_brain.chat.conversation.build_messages_for_llm",
            return_value=[{"role": "user", "content": "What changed?"}],
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
        patch("second_brain.db.get_db_client", return_value=SimpleNamespace(table=lambda _name: source_lookup)),
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
            json={"conversation_id": conv_id, "message": "What changed?"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "content": "Grounded answer",
        "sources": [
            {
                "source_id": "source-1",
                "title": "Structured Source",
                "url": "https://example.com/structured-source",
                "author": "Author",
                "score": 0.75,
                "published_at": "2026-03-23T00:00:00+00:00",
                "kind": "article",
                "tier": "analysis",
                "publisher": "Example.com",
            }
        ],
    }


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
        patch.dict(os.environ, TEST_ENV, clear=False),
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


def test_source_detail_endpoint_returns_structured_source_payload():
    """GET /api/sources/{id} should expose the new source detail fields."""
    from api.index import app

    row = {
        "id": "source-1",
        "title": "Structured Source",
        "author": "Author",
        "url": "https://example.com/structured-source",
        "published_at": "2026-03-23T00:00:00+00:00",
        "ingested_at": "2026-03-23T01:00:00+00:00",
        "updated_at": "2026-03-23T01:00:00+00:00",
        "source_type": "readwise",
        "readwise_id": "rw-1",
        "external_id": "rw-1",
        "kind": "article",
        "tier": "analysis",
        "publisher": "Example.com",
        "remote_updated_at": "2026-03-23T00:30:00+00:00",
        "parent_source_id": None,
        "thread_key": None,
        "language": "en",
        "metadata": {"text_source": "content"},
    }
    source_table = MagicMock()
    source_table.select.return_value.eq.return_value.execute.return_value.data = [row]

    fake_db = SimpleNamespace(table=lambda _name: source_table)
    with (
        patch.dict(os.environ, TEST_ENV, clear=False),
        patch("second_brain.db.get_db_client", return_value=fake_db),
        patch(
            "second_brain.analysis.extraction.get_source_analysis",
            return_value={"entities": [], "claims": [], "latest_run": None},
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/sources/source-1")

    assert response.status_code == 200
    assert response.json() == {
        **row,
        "analysis": {"entities": [], "claims": []},
        "latest_analysis_run": None,
    }


def test_analyze_source_endpoint_returns_completed_payload():
    """POST /api/sources/{id}/analyze should return the analysis result payload."""
    from api.index import app

    with (
        patch.dict(os.environ, TEST_ENV, clear=False),
        patch("second_brain.db.get_db_client", return_value=MagicMock()),
        patch("second_brain.providers.llm.get_llm_provider", return_value=MagicMock()),
        patch(
            "second_brain.analysis.extraction.analyze_source",
            return_value={
                "status": "completed",
                "run_id": "run-1",
                "entity_count": 2,
                "claim_count": 1,
                "evidence_count": 1,
                "claim_lens_count": 1,
                "link_count": 0,
                "analysis": {"entities": [], "claims": []},
            },
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/sources/source-1/analyze")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["run_id"] == "run-1"

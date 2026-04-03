"""Tests for insights and Phase 4 suggestion endpoints."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# GET /api/insights
# ---------------------------------------------------------------------------

def test_list_insights_returns_insights_and_unseen_count():
    """GET /api/insights should return all insights plus unseen_count."""
    from api.index import app
    from fastapi.testclient import TestClient

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "ins-1", "type": "digest", "title": "Weekly Digest", "body": "Lots of AI reading.",
         "seen": False, "created_at": "2026-04-02T10:00:00"},
        {"id": "ins-2", "type": "digest", "title": "Older Digest", "body": "Last week.",
         "seen": True, "created_at": "2026-03-25T10:00:00"},
    ]

    with patch("second_brain.db.get_db_client", return_value=mock_db):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/insights")

    assert response.status_code == 200
    data = response.json()
    assert data["unseen_count"] == 1
    assert len(data["insights"]) == 2
    assert data["insights"][0]["id"] == "ins-1"


# ---------------------------------------------------------------------------
# PATCH /api/insights/{id}/seen
# ---------------------------------------------------------------------------

def test_mark_insight_seen_calls_db_update():
    """PATCH /api/insights/{id}/seen should update the seen flag."""
    from api.index import app
    from fastapi.testclient import TestClient

    mock_db = MagicMock()
    # Chain: table().update().eq().execute()
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    with patch("second_brain.db.get_db_client", return_value=mock_db):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.patch("/api/insights/ins-123/seen")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_db.table.assert_called_with("insights")
    mock_db.table.return_value.update.assert_called_with({"seen": True})


# ---------------------------------------------------------------------------
# POST /api/insights/generate-digest
# ---------------------------------------------------------------------------

def test_generate_digest_no_articles():
    """POST /api/insights/generate-digest returns no_articles when corpus is empty."""
    from api.index import app
    from fastapi.testclient import TestClient

    with (
        patch("second_brain.db.get_db_client"),
        patch("second_brain.providers.llm.get_llm_provider"),
        patch(
            "second_brain.ingestion.insights.generate_digest",
            return_value=None,
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/insights/generate-digest")

    assert response.status_code == 200
    assert response.json()["status"] == "no_articles"


def test_generate_digest_creates_insight():
    """POST /api/insights/generate-digest returns ok + insight when articles exist."""
    from api.index import app
    from fastapi.testclient import TestClient

    fake_insight = {
        "id": "ins-new",
        "type": "digest",
        "title": "Weekly Digest — April 02, 2026",
        "body": "This week you read about AI safety and philosophy.",
        "seen": False,
        "created_at": "2026-04-02T12:00:00",
    }

    with (
        patch("second_brain.db.get_db_client"),
        patch("second_brain.providers.llm.get_llm_provider"),
        patch(
            "second_brain.ingestion.insights.generate_digest",
            return_value=fake_insight,
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/insights/generate-digest")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["insight"]["id"] == "ins-new"


# ---------------------------------------------------------------------------
# POST /api/insights/generate-suggestions
# ---------------------------------------------------------------------------

def test_generate_suggestions_no_results():
    """POST /api/insights/generate-suggestions returns no_suggestions when empty."""
    from api.index import app
    from fastapi.testclient import TestClient

    with (
        patch("second_brain.db.get_db_client"),
        patch(
            "second_brain.ingestion.insights.generate_suggestions",
            return_value=[],
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/insights/generate-suggestions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "no_suggestions"
    assert payload["insights"] == []


def test_generate_suggestions_returns_created_rows():
    """POST /api/insights/generate-suggestions returns new suggestions."""
    from api.index import app
    from fastapi.testclient import TestClient

    fake_rows = [
        {
            "id": "ins-s1",
            "type": "coverage_gap",
            "title": "Find a primary source for OpenClaw",
            "body": "OpenClaw has recent coverage but no primary source.",
            "summary": "No primary source yet",
            "status": "active",
            "seen": False,
            "created_at": "2026-04-02T12:00:00",
            "metadata": {"query": "OpenClaw investor relations"},
            "entities": [],
            "claims": [],
        }
    ]

    with (
        patch("second_brain.db.get_db_client"),
        patch(
            "second_brain.ingestion.insights.generate_suggestions",
            return_value=fake_rows,
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/insights/generate-suggestions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["insights"][0]["type"] == "coverage_gap"


# ---------------------------------------------------------------------------
# generate_digest unit test (pure function)
# ---------------------------------------------------------------------------

def test_generate_digest_groups_by_topic_and_calls_llm():
    """generate_digest should group sources by topic and call the LLM once."""
    from second_brain.ingestion.insights import generate_digest

    source_id = "src-aaa"
    mock_db = MagicMock()

    # sources table response
    mock_db.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value.data = [
        {"id": source_id, "title": "AI Safety 101", "author": "Alice", "published_at": None, "ingested_at": "2026-04-01"},
    ]
    # source_topics join response
    mock_db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"source_id": source_id, "topics": {"id": "top-1", "name": "AI Safety"}},
    ]
    # insert response
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "ins-1", "type": "digest", "title": "Weekly Digest", "body": "summary", "seen": False, "created_at": "2026-04-02"},
    ]

    mock_llm = MagicMock()
    mock_llm.complete.return_value = "This week was all about AI safety."

    result = generate_digest(mock_db, mock_llm)

    assert result is not None
    assert result["type"] == "digest"
    mock_llm.complete.assert_called_once()
    # LLM was given a context that includes the topic name
    call_args = mock_llm.complete.call_args[0][0]
    assert any("AI Safety" in msg["content"] for msg in call_args)


def test_generate_digest_returns_none_when_no_recent_sources():
    """generate_digest returns None if no sources were ingested this week."""
    from second_brain.ingestion.insights import generate_digest

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value.data = []

    mock_llm = MagicMock()
    result = generate_digest(mock_db, mock_llm)

    assert result is None
    mock_llm.complete.assert_not_called()

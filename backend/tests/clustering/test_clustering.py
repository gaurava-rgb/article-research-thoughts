"""Focused tests for Phase 3 topic assignment helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from second_brain.ingestion.clustering import (
    SIMILARITY_THRESHOLD,
    TopicAssignmentBatchResult,
    TopicAssignmentResult,
    assign_source_to_topic,
    assign_topic_to_source,
    assign_topics_to_unassigned_sources,
    find_best_topic,
    get_source_embedding,
    get_topic_sources_by_date,
    generate_topic_name,
    update_topic_centroid,
)


def test_get_source_embedding_returns_stored_vector():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"source_embedding": [0.1, 0.2, 0.3]}
    ]

    result = get_source_embedding("source-1", mock_db)

    assert result == [0.1, 0.2, 0.3]


def test_find_best_topic_returns_rpc_match():
    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value = SimpleNamespace(
        data=[{"topic_id": "topic-1", "topic_name": "AI", "similarity": 0.82}]
    )

    topic_id, similarity = find_best_topic([0.4, 0.5, 0.6], mock_db)

    assert topic_id == "topic-1"
    assert similarity == pytest.approx(0.82)
    mock_db.rpc.assert_called_once_with(
        "match_topic",
        {
            "query_embedding": [0.4, 0.5, 0.6],
            "match_threshold": SIMILARITY_THRESHOLD,
            "match_count": 1,
        },
    )


def test_find_best_topic_returns_none_when_rpc_finds_no_match():
    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value = SimpleNamespace(data=[])

    topic_id, similarity = find_best_topic([0.4, 0.5, 0.6], mock_db)

    assert topic_id is None
    assert similarity == 0.0


def test_generate_topic_name_returns_cleaned_single_line_name():
    llm_provider = MagicMock()
    llm_provider.complete.return_value = 'AI Safety and Governance."\nBecause it fits'

    topic_name = generate_topic_name(
        {
            "title": "How labs think about AI safety",
            "raw_text": "A long article preview.",
        },
        llm_provider,
    )

    assert topic_name == "AI Safety and Governance"


def test_update_topic_centroid_persists_normalized_mean_vector():
    mock_db = MagicMock()

    source_topics_table = MagicMock()
    source_topics_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"sources": {"source_embedding": [1.0, 0.0]}},
        {"sources": {"source_embedding": [0.0, 1.0]}},
    ]

    topics_table = MagicMock()
    topics_table.update.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": "topic-1"}]
    )

    mock_db.table.side_effect = lambda name: {
        "source_topics": source_topics_table,
        "topics": topics_table,
    }[name]

    centroid = update_topic_centroid("topic-1", mock_db)

    assert centroid == pytest.approx([0.70710678, 0.70710678])
    persisted = topics_table.update.call_args.args[0]["centroid_embedding"]
    assert persisted == pytest.approx([0.70710678, 0.70710678])


def test_update_topic_centroid_skips_write_without_embeddings():
    mock_db = MagicMock()

    source_topics_table = MagicMock()
    source_topics_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"sources": {"source_embedding": None}},
        {"sources": None},
    ]

    topics_table = MagicMock()
    mock_db.table.side_effect = lambda name: {
        "source_topics": source_topics_table,
        "topics": topics_table,
    }[name]

    centroid = update_topic_centroid("topic-1", mock_db)

    assert centroid is None
    topics_table.update.assert_not_called()


def test_assign_source_to_topic_inserts_membership_and_updates_centroid():
    mock_db = MagicMock()

    duplicate_query = MagicMock()
    duplicate_query.eq.return_value.eq.return_value.execute.return_value.data = []

    centroid_query = MagicMock()
    centroid_query.eq.return_value.execute.return_value.data = [
        {"sources": {"source_embedding": [1.0, 0.0]}},
        {"sources": {"source_embedding": [0.0, 1.0]}},
    ]

    source_topics_table = MagicMock()
    source_topics_table.select.side_effect = [duplicate_query, centroid_query]

    topics_table = MagicMock()
    mock_db.table.side_effect = lambda name: {
        "source_topics": source_topics_table,
        "topics": topics_table,
    }[name]

    inserted = assign_source_to_topic("source-1", "topic-1", mock_db)

    assert inserted is True
    source_topics_table.insert.assert_called_once_with(
        {"source_id": "source-1", "topic_id": "topic-1"}
    )
    topics_table.update.assert_called_once()


def test_assign_topic_to_source_uses_existing_topic_match():
    mock_db = MagicMock()
    llm_provider = MagicMock()

    with (
        patch("second_brain.ingestion.clustering.get_source_record") as mock_get_source_record,
        patch("second_brain.ingestion.clustering.find_best_topic") as mock_find_best_topic,
        patch("second_brain.ingestion.clustering.assign_source_to_topic") as mock_assign_source_to_topic,
    ):
        mock_get_source_record.return_value = {
            "id": "source-1",
            "title": "Article",
            "raw_text": "Body",
            "source_embedding": [0.1, 0.2],
        }
        mock_find_best_topic.return_value = ("topic-1", 0.82)

        result = assign_topic_to_source("source-1", mock_db, llm_provider)

    assert result.source_id == "source-1"
    assert result.topic_id == "topic-1"
    assert result.created_topic is False
    assert result.similarity == pytest.approx(0.82)
    assert result.reason == "assigned_existing_topic"
    mock_assign_source_to_topic.assert_called_once_with("source-1", "topic-1", mock_db)
    llm_provider.complete.assert_not_called()


def test_assign_topic_to_source_creates_topic_when_no_match():
    mock_db = MagicMock()
    llm_provider = MagicMock()

    with (
        patch("second_brain.ingestion.clustering.get_source_record") as mock_get_source_record,
        patch("second_brain.ingestion.clustering.find_best_topic") as mock_find_best_topic,
        patch("second_brain.ingestion.clustering.create_topic") as mock_create_topic,
        patch("second_brain.ingestion.clustering.assign_source_to_topic") as mock_assign_source_to_topic,
    ):
        mock_get_source_record.return_value = {
            "id": "source-1",
            "title": "Article",
            "raw_text": "Body",
            "source_embedding": [0.1, 0.2],
        }
        mock_find_best_topic.return_value = (None, 0.0)
        mock_create_topic.return_value = ("topic-new", "AI Safety")

        result = assign_topic_to_source("source-1", mock_db, llm_provider)

    assert result == TopicAssignmentResult(
        source_id="source-1",
        topic_id="topic-new",
        created_topic=True,
        similarity=0.0,
        reason="created_topic",
    )
    mock_create_topic.assert_called_once()
    mock_assign_source_to_topic.assert_called_once_with("source-1", "topic-new", mock_db)


def test_assign_topic_to_source_skips_when_embedding_missing():
    with patch("second_brain.ingestion.clustering.get_source_record") as mock_get_source_record:
        mock_get_source_record.return_value = {
            "id": "source-1",
            "title": "Article",
            "raw_text": "Body",
            "source_embedding": None,
        }
        result = assign_topic_to_source(
            "source-1",
            MagicMock(),
            MagicMock(),
        )

    assert result == TopicAssignmentResult(
        source_id="source-1",
        topic_id=None,
        created_topic=False,
        similarity=0.0,
        reason="missing_source_embedding",
    )


def test_assign_topics_to_unassigned_sources_processes_only_unassigned_rows():
    mock_db = MagicMock()
    sources_table = MagicMock()
    source_topics_table = MagicMock()

    sources_table.select.return_value.execute.return_value.data = [
        {"id": "source-1"},
        {"id": "source-2"},
        {"id": "source-3"},
    ]
    source_topics_table.select.return_value.execute.return_value.data = [
        {"source_id": "source-2"}
    ]

    mock_db.table.side_effect = lambda name: {
        "sources": sources_table,
        "source_topics": source_topics_table,
    }[name]

    with patch("second_brain.ingestion.clustering.assign_topic_to_source") as mock_assign:
        mock_assign.side_effect = [
            TopicAssignmentResult(
                source_id="source-1",
                topic_id="topic-1",
                created_topic=False,
                similarity=0.8,
                reason="assigned_existing_topic",
            ),
            TopicAssignmentResult(
                source_id="source-3",
                topic_id=None,
                created_topic=False,
                similarity=0.0,
                reason="missing_source_embedding",
            ),
        ]

        result = assign_topics_to_unassigned_sources(mock_db, MagicMock())

    assert result == TopicAssignmentBatchResult(
        processed_count=2,
        assigned_existing_count=1,
        created_topic_count=0,
        skipped_missing_embedding_count=1,
    )
    assert [call.args[0] for call in mock_assign.call_args_list] == ["source-1", "source-3"]


def test_get_topic_sources_by_date_filters_by_published_at():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "sources": {
                "id": "source-old",
                "title": "Old article",
                "author": "Author",
                "url": "https://example.com/old",
                "published_at": "2024-01-15T00:00:00Z",
                "ingested_at": "2026-03-23T00:00:00Z",
            }
        },
        {
            "sources": {
                "id": "source-new",
                "title": "New article",
                "author": "Author",
                "url": "https://example.com/new",
                "published_at": "2025-02-01T00:00:00Z",
                "ingested_at": "2026-03-23T00:00:00Z",
            }
        },
    ]

    rows = get_topic_sources_by_date("topic-1", after="2025-01-01", before=None, db=mock_db)

    assert [row["id"] for row in rows] == ["source-new"]


def test_get_topic_sources_by_date_uses_ingested_at_when_published_at_is_missing():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "sources": {
                "id": "source-1",
                "title": "No published date",
                "author": "Author",
                "url": "https://example.com/article",
                "published_at": None,
                "ingested_at": "2024-06-01T09:30:00Z",
            }
        }
    ]

    rows = get_topic_sources_by_date("topic-1", after="2024-01-01", before=None, db=mock_db)

    assert [row["id"] for row in rows] == ["source-1"]

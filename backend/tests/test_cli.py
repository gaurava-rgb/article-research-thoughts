"""CLI behavior tests for resumable sync and topic-assignment flows."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def test_sync_completes_without_error_when_no_new_articles():
    from second_brain import cli as cli_module

    db = MagicMock(name="db")
    embed_provider = MagicMock(name="embed_provider")
    cfg = SimpleNamespace(
        readwise=SimpleNamespace(token="test-token"),
        chunking=SimpleNamespace(target_tokens=500, overlap_tokens=50),
    )

    with (
        patch("second_brain.config.cfg", cfg),
        patch("second_brain.db.get_db_client", return_value=db),
        patch(
            "second_brain.providers.embeddings.get_embedding_provider",
            return_value=embed_provider,
        ),
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
            return_value=(0, 1, []),
        ),
    ):
        cli_module.sync(limit=None)  # should not raise


def test_assign_topics_processes_unassigned_sources():
    from second_brain import cli as cli_module

    db = object()
    llm_provider = MagicMock(name="llm_provider")
    result = SimpleNamespace(
        processed_count=3,
        assigned_existing_count=2,
        created_topic_count=1,
        skipped_missing_embedding_count=0,
    )

    with (
        patch("second_brain.db.get_db_client", return_value=db),
        patch(
            "second_brain.providers.llm.get_llm_provider",
            return_value=llm_provider,
        ),
        patch(
            "second_brain.ingestion.clustering.assign_topics_to_unassigned_sources",
            return_value=result,
        ) as mock_assign_topics,
    ):
        cli_module.assign_topics(limit=3)

    mock_assign_topics.assert_called_once_with(
        db,
        llm_provider,
        limit=3,
    )

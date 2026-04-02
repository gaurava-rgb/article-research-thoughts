"""Tests for Readwise ingestion storage behavior."""

from contextlib import AbstractContextManager
from types import SimpleNamespace
from unittest.mock import MagicMock

from second_brain.ingestion.readwise import (
    MAX_SOURCE_EMBEDDING_TOKENS,
    ReadwiseArticle,
    backfill_missing_chunks,
    backfill_missing_source_embeddings,
    fetch_all_articles,
    store_articles,
)


class FakeSourcesTable:
    def __init__(
        self,
        existing_readwise_ids: set[str],
        duplicate_on_insert_ids: set[str] | None = None,
        source_rows: list[dict] | None = None,
    ):
        self._existing_readwise_ids = existing_readwise_ids
        self._duplicate_on_insert_ids = duplicate_on_insert_ids or set()
        self._source_rows = source_rows or []
        self.inserted_rows: list[dict] = []
        self.updated_rows: list[dict] = []
        self._selected_readwise_id: str | None = None
        self._selected_id: str | None = None
        self._mode: str | None = None
        self._pending_insert_payload: dict | None = None
        self._pending_update_payload: dict | None = None

    def select(self, _columns: str) -> "FakeSourcesTable":
        self._mode = "select"
        return self

    def eq(self, column: str, value: str) -> "FakeSourcesTable":
        assert column in {"readwise_id", "id"}
        if column == "readwise_id":
            self._selected_readwise_id = value
        else:
            self._selected_id = value
        return self

    def insert(self, payload: dict) -> "FakeSourcesTable":
        self._mode = "insert"
        self._pending_insert_payload = payload
        return self

    def update(self, payload: dict) -> "FakeSourcesTable":
        self._mode = "update"
        self._pending_update_payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        if self._mode == "select":
            if self._selected_readwise_id is not None:
                exists = self._selected_readwise_id in self._existing_readwise_ids
                result = [{"id": "existing-source-id"}] if exists else []
                self._selected_readwise_id = None
                return SimpleNamespace(data=result)
            return SimpleNamespace(data=self._source_rows)

        if self._mode == "insert":
            assert self._pending_insert_payload is not None
            readwise_id = self._pending_insert_payload["readwise_id"]
            if readwise_id in self._duplicate_on_insert_ids:
                raise RuntimeError(
                    "{'message': 'duplicate key value violates unique constraint "
                    "\"sources_readwise_id_key\"', 'code': '23505'}"
                )
            self.inserted_rows.append(self._pending_insert_payload)
            return SimpleNamespace(data=[])

        if self._mode == "update":
            assert self._pending_update_payload is not None
            assert self._selected_id is not None
            self.updated_rows.append(
                {"id": self._selected_id, **self._pending_update_payload}
            )
            for row in self._source_rows:
                if row["id"] == self._selected_id:
                    row.update(self._pending_update_payload)
                    break
            self._selected_id = None
            return SimpleNamespace(data=[])

        raise AssertionError("Unexpected execute() call without select() or insert().")


class FakeChunksTable:
    def __init__(self, chunk_rows: list[dict] | None = None):
        self._chunk_rows = chunk_rows or []
        self._mode: str | None = None
        self._range_start: int | None = None
        self._range_end: int | None = None

    def select(self, _columns: str) -> "FakeChunksTable":
        self._mode = "select"
        return self

    def range(self, start: int, end: int) -> "FakeChunksTable":
        """Support paginated selects used by backfill_missing_chunks."""
        self._range_start = start
        self._range_end = end
        return self

    def execute(self) -> SimpleNamespace:
        if self._mode == "select":
            # If range() was called, return the appropriate page slice.
            # For tests, returning all rows on the first page (empty on subsequent) is
            # enough to exercise the while-True pagination loop correctly.
            if self._range_start is not None:
                page = self._chunk_rows[self._range_start:self._range_end + 1]
                # Reset so the next call (next page) returns empty → terminates loop
                self._chunk_rows = []
                return SimpleNamespace(data=page)
            return SimpleNamespace(data=self._chunk_rows)
        raise AssertionError("Unexpected execute() call without select().")


class FakeDB:
    def __init__(
        self,
        existing_readwise_ids: set[str],
        duplicate_on_insert_ids: set[str] | None = None,
        source_rows: list[dict] | None = None,
        chunk_rows: list[dict] | None = None,
    ):
        self.sources = FakeSourcesTable(
            existing_readwise_ids,
            duplicate_on_insert_ids,
            source_rows,
        )
        self.chunks = FakeChunksTable(chunk_rows)

    def table(self, name: str) -> FakeSourcesTable | FakeChunksTable:
        if name == "sources":
            return self.sources
        if name == "chunks":
            return self.chunks
        raise AssertionError(f"Unexpected table: {name}")


class FakeReadwiseResponse:
    def __init__(self, payload: dict):
        self.status_code = 200
        self._payload = payload
        self.text = ""

    def json(self) -> dict:
        return self._payload


class FakeReadwiseClient(AbstractContextManager):
    def __init__(self, payloads: list[dict]):
        self._payloads = payloads
        self.request_params: list[dict] = []
        self._idx = 0

    def __enter__(self) -> "FakeReadwiseClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, headers: dict, params: dict) -> FakeReadwiseResponse:
        self.request_params.append(params.copy())
        payload = self._payloads[self._idx]
        self._idx += 1
        return FakeReadwiseResponse(payload)


def test_store_articles_persists_source_embedding_only_for_new_articles():
    existing_article = ReadwiseArticle(
        readwise_id="existing-id",
        title="Existing",
        author="Author",
        url="https://example.com/existing",
        published_at="2026-03-01",
        text="Existing article text that should be skipped because it already exists.",
        ingested_at="2026-03-23T00:00:00Z",
    )
    new_article = ReadwiseArticle(
        readwise_id="new-id",
        title="New",
        author="Author",
        url="https://example.com/new",
        published_at="2026-03-02",
        text="New article text that is long enough to generate a whole-source embedding.",
        ingested_at="2026-03-23T00:00:00Z",
    )
    db = FakeDB(existing_readwise_ids={"existing-id"})
    embed_provider = MagicMock()
    embed_provider.embed.return_value = [[0.1, 0.2, 0.3]]

    new_count, skipped_count, _ = store_articles(
        [existing_article, new_article],
        db,
        embed_provider=embed_provider,
    )

    assert new_count == 1
    assert skipped_count == 1
    embed_provider.embed.assert_called_once_with([new_article.text])
    assert db.sources.inserted_rows == [
        {
            "title": new_article.title,
            "author": new_article.author,
            "url": new_article.url,
            "published_at": new_article.published_at,
            "ingested_at": new_article.ingested_at,
            "readwise_id": new_article.readwise_id,
            "raw_text": new_article.text,
            "source_embedding": [0.1, 0.2, 0.3],
        }
    ]


def test_fetch_all_articles_uses_html_content_when_plain_content_is_missing(monkeypatch):
    html_body = """
    <article>
      <h1>Example title</h1>
      <p>This is a long article body that should be recovered from html content.</p>
      <p>It contains enough words to clear the minimum text length threshold.</p>
    </article>
    """
    fake_client = FakeReadwiseClient(
        [
            {
                "results": [
                    {
                        "id": "html-only-id",
                        "title": "HTML only article",
                        "author": "Author",
                        "url": "https://read.readwise.io/read/html-only-id",
                        "published_date": "2026-03-23",
                        "content": None,
                        "html_content": html_body,
                    }
                ],
                "nextPageCursor": None,
            }
        ]
    )

    monkeypatch.setattr(
        "second_brain.ingestion.readwise.httpx.Client",
        lambda timeout=30: fake_client,
    )

    articles = fetch_all_articles("test-token")

    assert fake_client.request_params == [{"withHtmlContent": "true"}]
    assert len(articles) == 1
    assert articles[0].readwise_id == "html-only-id"
    assert articles[0].title == "HTML only article"
    assert "This is a long article body" in articles[0].text
    assert "<p>" not in articles[0].text


def test_store_articles_truncates_long_source_text_before_embedding():
    long_text = "token " * (MAX_SOURCE_EMBEDDING_TOKENS + 500)
    article = ReadwiseArticle(
        readwise_id="long-id",
        title="Long article",
        author="Author",
        url="https://example.com/long",
        published_at="2026-03-23",
        text=long_text,
        ingested_at="2026-03-23T00:00:00Z",
    )
    db = FakeDB(existing_readwise_ids=set())
    embed_provider = MagicMock()
    embed_provider.embed.return_value = [[0.4, 0.5, 0.6]]

    store_articles([article], db, embed_provider=embed_provider)

    embedded_text = embed_provider.embed.call_args.args[0][0]
    assert len(embedded_text) < len(long_text)
    assert db.sources.inserted_rows[0]["source_embedding"] == [0.4, 0.5, 0.6]


def test_store_articles_treats_duplicate_insert_race_as_skipped():
    article = ReadwiseArticle(
        readwise_id="racy-id",
        title="Race",
        author="Author",
        url="https://example.com/race",
        published_at="2026-03-23",
        text="This article is long enough to make it through the ingestion filter.",
        ingested_at="2026-03-23T00:00:00Z",
    )
    db = FakeDB(existing_readwise_ids=set(), duplicate_on_insert_ids={"racy-id"})
    embed_provider = MagicMock()
    embed_provider.embed.return_value = [[0.7, 0.8, 0.9]]

    new_count, skipped_count, _ = store_articles([article], db, embed_provider=embed_provider)

    assert new_count == 0
    assert skipped_count == 1
    assert db.sources.inserted_rows == []


def test_backfill_missing_source_embeddings_repairs_only_null_rows():
    source_rows = [
        {
            "id": "missing-source-id",
            "readwise_id": "missing-id",
            "raw_text": "This source has enough text to generate a repaired source embedding.",
            "source_embedding": None,
        },
        {
            "id": "already-embedded-id",
            "readwise_id": "already-id",
            "raw_text": "This source already has a source embedding and should be untouched.",
            "source_embedding": [9.9, 8.8, 7.7],
        },
        {
            "id": "missing-text-id",
            "readwise_id": "missing-text",
            "raw_text": "",
            "source_embedding": None,
        },
    ]
    db = FakeDB(existing_readwise_ids=set(), source_rows=source_rows)
    embed_provider = MagicMock()
    embed_provider.embed.return_value = [[0.3, 0.2, 0.1]]

    missing_count, updated_count, skipped_no_text_count = backfill_missing_source_embeddings(
        db,
        embed_provider,
    )

    assert missing_count == 2
    assert updated_count == 1
    assert skipped_no_text_count == 1
    embed_provider.embed.assert_called_once_with(
        [source_rows[0]["raw_text"]]
    )
    assert db.sources.updated_rows == [
        {
            "id": "missing-source-id",
            "source_embedding": [0.3, 0.2, 0.1],
        }
    ]
    assert source_rows[0]["source_embedding"] == [0.3, 0.2, 0.1]
    assert source_rows[1]["source_embedding"] == [9.9, 8.8, 7.7]


def test_backfill_missing_chunks_repairs_only_sources_without_chunk_rows(monkeypatch):
    source_rows = [
        {
            "id": "missing-source-id",
            "readwise_id": "missing-id",
            "title": "Needs repair",
            "raw_text": "This source has enough text to produce repaired chunk coverage.",
        },
        {
            "id": "already-chunked-id",
            "readwise_id": "already-id",
            "title": "Already chunked",
            "raw_text": "This source already has chunks and should be skipped.",
        },
        {
            "id": "missing-text-id",
            "readwise_id": "missing-text",
            "title": "No raw text",
            "raw_text": "",
        },
    ]
    chunk_rows = [{"source_id": "already-chunked-id"}]
    db = FakeDB(
        existing_readwise_ids=set(),
        source_rows=source_rows,
        chunk_rows=chunk_rows,
    )
    embed_provider = MagicMock()

    fake_chunks = [SimpleNamespace(content="chunk", source_id="missing-source-id", chunk_index=0, token_count=42)]
    chunk_text_mock = MagicMock(return_value=fake_chunks)
    store_chunks_mock = MagicMock(return_value=1)
    monkeypatch.setattr("second_brain.ingestion.chunker.chunk_text", chunk_text_mock)
    monkeypatch.setattr(
        "second_brain.ingestion.chunker.store_chunks_with_embeddings",
        store_chunks_mock,
    )

    missing_count, repaired_source_count, total_chunks, skipped_no_text_count = backfill_missing_chunks(
        db,
        embed_provider,
        target_tokens=500,
        overlap_tokens=50,
    )

    assert missing_count == 2
    assert repaired_source_count == 1
    assert total_chunks == 1
    assert skipped_no_text_count == 1
    chunk_text_mock.assert_called_once_with(
        source_rows[0]["raw_text"],
        source_id="missing-source-id",
        target_tokens=500,
        overlap_tokens=50,
    )
    store_chunks_mock.assert_called_once_with(fake_chunks, embed_provider, db)

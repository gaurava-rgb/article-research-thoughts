"""Tests for Phase 2 source analysis extraction."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from second_brain.analysis.extraction import analyze_source, get_source_analysis


class FakeTable:
    def __init__(self, db: "FakeDB", name: str):
        self._db = db
        self._name = name
        self._mode: str | None = None
        self._filters: list[tuple[str, str, object]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._payload: dict | None = None

    def select(self, _columns: str) -> "FakeTable":
        self._mode = "select"
        return self

    def eq(self, column: str, value: object) -> "FakeTable":
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[object]) -> "FakeTable":
        self._filters.append(("in", column, values))
        return self

    def order(self, column: str, desc: bool = False) -> "FakeTable":
        self._order = (column, desc)
        return self

    def limit(self, count: int) -> "FakeTable":
        self._limit = count
        return self

    def insert(self, payload: dict) -> "FakeTable":
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict) -> "FakeTable":
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self) -> "FakeTable":
        self._mode = "delete"
        return self

    def execute(self) -> SimpleNamespace:
        rows = self._db.rows[self._name]
        filtered = self._apply_filters(rows)

        if self._mode == "select":
            result = [dict(row) for row in filtered]
            if self._order is not None:
                column, desc = self._order
                result.sort(key=lambda row: (row.get(column) is None, row.get(column)), reverse=desc)
            if self._limit is not None:
                result = result[: self._limit]
            self._reset()
            return SimpleNamespace(data=result)

        if self._mode == "insert":
            assert self._payload is not None
            inserted = dict(self._payload)
            if "id" not in inserted and self._name not in {"source_entities", "claim_lenses"}:
                inserted["id"] = self._db.next_id(self._name)
            rows.append(inserted)
            self._reset()
            return SimpleNamespace(data=[dict(inserted)])

        if self._mode == "update":
            assert self._payload is not None
            for row in filtered:
                row.update(self._payload)
            self._reset()
            return SimpleNamespace(data=[dict(row) for row in filtered])

        if self._mode == "delete":
            remaining = [row for row in rows if row not in filtered]
            self._db.rows[self._name] = remaining
            self._reset()
            return SimpleNamespace(data=[])

        raise AssertionError(f"Unexpected mode for {self._name}: {self._mode}")

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        filtered = rows
        for filter_type, column, value in self._filters:
            if filter_type == "eq":
                filtered = [row for row in filtered if row.get(column) == value]
            elif filter_type == "in":
                allowed = set(value)
                filtered = [row for row in filtered if row.get(column) in allowed]
        return filtered

    def _reset(self) -> None:
        self._mode = None
        self._filters = []
        self._order = None
        self._limit = None
        self._payload = None


class FakeDB:
    def __init__(self, rows: dict[str, list[dict]]):
        self.rows = rows
        self._counters: dict[str, int] = {}

    def table(self, name: str) -> FakeTable:
        self.rows.setdefault(name, [])
        return FakeTable(self, name)

    def next_id(self, table_name: str) -> str:
        self._counters[table_name] = self._counters.get(table_name, 0) + 1
        return f"{table_name}-{self._counters[table_name]}"


class FakeLLM:
    def __init__(self, response: str):
        self._response = response
        self._model = "fake-llm"

    def complete(self, _messages: list[dict[str, str]], **_kwargs) -> str:
        return self._response


def build_fake_db() -> FakeDB:
    source_text = (
        "Acme launched Atlas, a new AI assistant for analysts. "
        "Revenue from the analytics segment grew 30% year over year. "
        "Management said the launch may pressure Contoso in enterprise analyst software."
    )
    return FakeDB(
        {
            "sources": [
                {
                    "id": "source-1",
                    "title": "Acme Ships Atlas",
                    "author": "Analyst",
                    "url": "https://example.com/acme-atlas",
                    "published_at": "2026-04-01T00:00:00+00:00",
                    "source_type": "readwise",
                    "readwise_id": "rw-1",
                    "external_id": "rw-1",
                    "kind": "article",
                    "tier": "analysis",
                    "publisher": "Example",
                    "remote_updated_at": None,
                    "parent_source_id": None,
                    "thread_key": None,
                    "language": "en",
                    "metadata": {},
                    "ingested_at": "2026-04-02T00:00:00+00:00",
                    "updated_at": "2026-04-02T00:00:00+00:00",
                    "raw_text": source_text,
                }
            ],
            "chunks": [
                {
                    "id": "chunk-1",
                    "source_id": "source-1",
                    "chunk_index": 0,
                    "content": (
                        "Acme launched Atlas, a new AI assistant for analysts. "
                        "Revenue from the analytics segment grew 30% year over year."
                    ),
                    "start_char": 0,
                    "end_char": 117,
                },
                {
                    "id": "chunk-2",
                    "source_id": "source-1",
                    "chunk_index": 1,
                    "content": "Management said the launch may pressure Contoso in enterprise analyst software.",
                    "start_char": 118,
                    "end_char": 201,
                },
            ],
            "lenses": [
                {
                    "id": "lens-1",
                    "slug": "distribution",
                    "name": "Distribution",
                    "description": "Go-to-market and channel leverage.",
                },
                {
                    "id": "lens-2",
                    "slug": "business-model",
                    "name": "Business Model",
                    "description": "Revenue and monetization.",
                },
            ],
            "processing_runs": [],
            "entities": [],
            "entity_aliases": [],
            "source_entities": [],
            "claims": [],
            "claim_evidence": [],
            "claim_lenses": [],
            "claim_links": [],
        }
    )


def test_analyze_source_is_rerunnable_and_idempotent():
    db = build_fake_db()
    llm = FakeLLM(
        json.dumps(
            {
                "entities": [
                    {
                        "name": "Acme",
                        "entity_type": "company",
                        "aliases": ["Acme Corp"],
                        "role": "primary",
                        "mention_count": 3,
                        "salience": 0.95,
                        "metadata": {},
                    },
                    {
                        "name": "Atlas",
                        "entity_type": "product",
                        "aliases": [],
                        "role": "product",
                        "mention_count": 2,
                        "salience": 0.9,
                        "metadata": {},
                    },
                    {
                        "name": "Contoso",
                        "entity_type": "company",
                        "aliases": [],
                        "role": "competitor",
                        "mention_count": 1,
                        "salience": 0.7,
                        "metadata": {},
                    },
                ],
                "claims": [
                    {
                        "claim_text": "Acme launched Atlas, a new AI assistant for analysts.",
                        "claim_type": "product",
                        "modality": "reported",
                        "stance": "positive",
                        "subject_entity": "Acme",
                        "object_entity": "Atlas",
                        "normalized_claim": "acme launched atlas for analysts",
                        "confidence": 0.91,
                        "importance": 0.89,
                        "lenses": ["distribution"],
                        "evidence": [
                            {
                                "quote": "Acme launched Atlas, a new AI assistant for analysts.",
                                "confidence": 0.95,
                            }
                        ],
                        "links": [
                            {
                                "target_claim": 2,
                                "link_type": "leads_to",
                                "confidence": 0.76,
                                "explanation": "The launch creates the competitive effect.",
                            }
                        ],
                    },
                    {
                        "claim_text": "The Atlas launch may pressure Contoso in enterprise analyst software.",
                        "claim_type": "competitive",
                        "modality": "speculative",
                        "stance": "negative",
                        "subject_entity": "Atlas",
                        "object_entity": "Contoso",
                        "normalized_claim": "atlas may pressure contoso in analyst software",
                        "confidence": 0.82,
                        "importance": 0.78,
                        "lenses": ["distribution", "business-model"],
                        "evidence": [
                            {
                                "quote": "may pressure Contoso in enterprise analyst software.",
                                "confidence": 0.87,
                            }
                        ],
                        "links": [],
                    },
                    {
                        "claim_text": "Revenue from the analytics segment grew 30% year over year.",
                        "claim_type": "financial",
                        "modality": "reported",
                        "stance": "positive",
                        "subject_entity": "Acme",
                        "object_entity": None,
                        "normalized_claim": "analytics segment revenue grew 30 percent year over year",
                        "confidence": 0.88,
                        "importance": 0.8,
                        "lenses": ["business-model"],
                        "evidence": [
                            {
                                "quote": "Revenue from the analytics segment grew 30% year over year.",
                                "confidence": 0.9,
                            }
                        ],
                        "links": [
                            {
                                "target_claim": 2,
                                "link_type": "amplifies",
                                "confidence": 0.64,
                                "explanation": "Growth makes the launch strategically stronger.",
                            }
                        ],
                    },
                ],
            }
        )
    )

    first = analyze_source("source-1", db, llm)
    second = analyze_source("source-1", db, llm)
    analysis = get_source_analysis("source-1", db)

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert len(db.rows["processing_runs"]) == 2
    assert [run["status"] for run in db.rows["processing_runs"]] == ["completed", "completed"]

    assert len(db.rows["entities"]) == 3
    assert len(db.rows["entity_aliases"]) == 1
    assert len(db.rows["source_entities"]) == 3
    assert len(db.rows["claims"]) == 3
    assert len(db.rows["claim_evidence"]) == 3
    assert len(db.rows["claim_lenses"]) == 4
    assert len(db.rows["claim_links"]) == 2

    assert len(analysis["entities"]) == 3
    assert len(analysis["claims"]) == 3
    assert analysis["latest_run"]["status"] == "completed"
    assert analysis["latest_run"]["metadata"]["claim_count"] == 3

    first_claim = analysis["claims"][0]
    evidence_quotes = {evidence["evidence_text"] for evidence in first_claim["evidence"]}
    assert "Acme launched Atlas, a new AI assistant for analysts." in evidence_quotes
    all_chunk_indices = {
        evidence["chunk_index"]
        for claim in analysis["claims"]
        for evidence in claim["evidence"]
    }
    assert all_chunk_indices == {0, 1}


def test_analyze_source_marks_processing_run_failed_on_invalid_json():
    db = build_fake_db()
    llm = FakeLLM("not valid json")

    with pytest.raises(ValueError):
        analyze_source("source-1", db, llm)

    assert len(db.rows["processing_runs"]) == 1
    run = db.rows["processing_runs"][0]
    assert run["status"] == "failed"
    assert run["metadata"]["source_id"] == "source-1"
    assert "JSON" in run["metadata"]["error"]

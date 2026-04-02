"""Tests for Phase 3 entity dossier helpers."""

from __future__ import annotations

from types import SimpleNamespace

from second_brain.analysis.dossier import get_entity_dossier, list_entities


class FakeTable:
    def __init__(self, db: "FakeDB", name: str):
        self._db = db
        self._name = name
        self._filters: list[tuple[str, str, object]] = []

    def select(self, _columns: str) -> "FakeTable":
        return self

    def eq(self, column: str, value: object) -> "FakeTable":
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: list[object]) -> "FakeTable":
        self._filters.append(("in", column, values))
        return self

    def execute(self) -> SimpleNamespace:
        rows = self._db.rows.setdefault(self._name, [])
        filtered = rows
        for filter_type, column, value in self._filters:
            if filter_type == "eq":
                filtered = [row for row in filtered if row.get(column) == value]
            elif filter_type == "in":
                allowed = set(value)
                filtered = [row for row in filtered if row.get(column) in allowed]
        self._filters = []
        return SimpleNamespace(data=[dict(row) for row in filtered])


class FakeDB:
    def __init__(self, rows: dict[str, list[dict]]):
        self.rows = rows

    def table(self, name: str) -> FakeTable:
        return FakeTable(self, name)


def build_fake_db() -> FakeDB:
    return FakeDB(
        {
            "sources": [
                {
                    "id": "source-1",
                    "title": "Acme Ships Atlas",
                    "url": "https://example.com/acme-atlas",
                    "source_type": "readwise",
                    "kind": "article",
                    "tier": "analysis",
                    "published_at": "2026-03-15T00:00:00+00:00",
                    "ingested_at": "2026-03-16T00:00:00+00:00",
                },
                {
                    "id": "source-2",
                    "title": "Atlas Pressures Contoso",
                    "url": "https://example.com/atlas-contoso",
                    "source_type": "readwise",
                    "kind": "article",
                    "tier": "analysis",
                    "published_at": "2026-03-20T00:00:00+00:00",
                    "ingested_at": "2026-03-21T00:00:00+00:00",
                },
                {
                    "id": "source-3",
                    "title": "Acme Analytics Growth",
                    "url": "https://example.com/acme-growth",
                    "source_type": "readwise",
                    "kind": "article",
                    "tier": "analysis",
                    "published_at": "2026-03-25T00:00:00+00:00",
                    "ingested_at": "2026-03-26T00:00:00+00:00",
                },
                {
                    "id": "source-4",
                    "title": "Skeptical View On Acme Growth",
                    "url": "https://example.com/acme-skeptical",
                    "source_type": "readwise",
                    "kind": "article",
                    "tier": "analysis",
                    "published_at": "2026-03-27T00:00:00+00:00",
                    "ingested_at": "2026-03-28T00:00:00+00:00",
                },
            ],
            "entities": [
                {
                    "id": "entity-acme",
                    "canonical_name": "Acme",
                    "entity_type": "company",
                    "ticker": "ACME",
                    "metadata": {},
                },
                {
                    "id": "entity-atlas",
                    "canonical_name": "Atlas",
                    "entity_type": "product",
                    "ticker": None,
                    "metadata": {},
                },
                {
                    "id": "entity-contoso",
                    "canonical_name": "Contoso",
                    "entity_type": "company",
                    "ticker": None,
                    "metadata": {},
                },
                {
                    "id": "entity-market",
                    "canonical_name": "Enterprise Analyst Software",
                    "entity_type": "market",
                    "ticker": None,
                    "metadata": {},
                },
            ],
            "entity_aliases": [
                {
                    "entity_id": "entity-acme",
                    "alias": "Acme Corp",
                    "alias_type": "name",
                    "confidence": 0.9,
                }
            ],
            "source_entities": [
                {"source_id": "source-1", "entity_id": "entity-acme"},
                {"source_id": "source-1", "entity_id": "entity-atlas"},
                {"source_id": "source-2", "entity_id": "entity-atlas"},
                {"source_id": "source-2", "entity_id": "entity-contoso"},
                {"source_id": "source-3", "entity_id": "entity-acme"},
                {"source_id": "source-4", "entity_id": "entity-acme"},
            ],
            "claims": [
                {
                    "id": "claim-1",
                    "source_id": "source-1",
                    "subject_entity_id": "entity-acme",
                    "object_entity_id": "entity-atlas",
                    "claim_type": "product",
                    "modality": "reported",
                    "stance": "positive",
                    "claim_text": "Acme launched Atlas for analysts.",
                    "normalized_claim": "acme launched atlas for analysts",
                    "event_at": "2026-03-15T00:00:00+00:00",
                    "event_end_at": None,
                    "confidence": 0.92,
                    "importance": 0.91,
                    "extraction_run_id": "run-1",
                    "metadata": {},
                    "created_at": "2026-03-15T00:00:00+00:00",
                },
                {
                    "id": "claim-2",
                    "source_id": "source-2",
                    "subject_entity_id": "entity-atlas",
                    "object_entity_id": "entity-contoso",
                    "claim_type": "competitive",
                    "modality": "speculative",
                    "stance": "negative",
                    "claim_text": "The Atlas launch may pressure Contoso.",
                    "normalized_claim": "atlas may pressure contoso",
                    "event_at": None,
                    "event_end_at": None,
                    "confidence": 0.8,
                    "importance": 0.78,
                    "extraction_run_id": "run-1",
                    "metadata": {},
                    "created_at": "2026-03-20T00:00:00+00:00",
                },
                {
                    "id": "claim-3",
                    "source_id": "source-3",
                    "subject_entity_id": "entity-acme",
                    "object_entity_id": None,
                    "claim_type": "financial",
                    "modality": "reported",
                    "stance": "positive",
                    "claim_text": "Acme analytics revenue grew 30% year over year.",
                    "normalized_claim": "acme analytics revenue grew 30 percent year over year",
                    "event_at": "2026-03-25T00:00:00+00:00",
                    "event_end_at": None,
                    "confidence": 0.88,
                    "importance": 0.86,
                    "extraction_run_id": "run-1",
                    "metadata": {},
                    "created_at": "2026-03-25T00:00:00+00:00",
                },
                {
                    "id": "claim-4",
                    "source_id": "source-4",
                    "subject_entity_id": "entity-acme",
                    "object_entity_id": None,
                    "claim_type": "financial",
                    "modality": "asserted",
                    "stance": "negative",
                    "claim_text": "Acme analytics revenue growth is overstated.",
                    "normalized_claim": "acme analytics revenue grew 30 percent year over year",
                    "event_at": "2026-03-27T00:00:00+00:00",
                    "event_end_at": None,
                    "confidence": 0.73,
                    "importance": 0.74,
                    "extraction_run_id": "run-2",
                    "metadata": {},
                    "created_at": "2026-03-27T00:00:00+00:00",
                },
            ],
            "claim_evidence": [
                {
                    "id": "evidence-1",
                    "claim_id": "claim-1",
                    "source_id": "source-1",
                    "chunk_id": "chunk-1",
                    "evidence_text": "Acme launched Atlas for analysts.",
                    "start_char": 0,
                    "end_char": 33,
                    "confidence": 0.95,
                    "created_at": "2026-03-15T00:00:00+00:00",
                },
                {
                    "id": "evidence-2",
                    "claim_id": "claim-2",
                    "source_id": "source-2",
                    "chunk_id": "chunk-2",
                    "evidence_text": "may pressure Contoso",
                    "start_char": 14,
                    "end_char": 34,
                    "confidence": 0.87,
                    "created_at": "2026-03-20T00:00:00+00:00",
                },
                {
                    "id": "evidence-3",
                    "claim_id": "claim-3",
                    "source_id": "source-3",
                    "chunk_id": "chunk-3",
                    "evidence_text": "revenue grew 30% year over year",
                    "start_char": 5,
                    "end_char": 36,
                    "confidence": 0.9,
                    "created_at": "2026-03-25T00:00:00+00:00",
                },
                {
                    "id": "evidence-4",
                    "claim_id": "claim-4",
                    "source_id": "source-4",
                    "chunk_id": "chunk-4",
                    "evidence_text": "growth is overstated",
                    "start_char": 12,
                    "end_char": 32,
                    "confidence": 0.82,
                    "created_at": "2026-03-27T00:00:00+00:00",
                },
            ],
            "chunks": [
                {"id": "chunk-1", "chunk_index": 0},
                {"id": "chunk-2", "chunk_index": 1},
                {"id": "chunk-3", "chunk_index": 0},
                {"id": "chunk-4", "chunk_index": 0},
            ],
            "lenses": [
                {
                    "id": "lens-1",
                    "slug": "distribution",
                    "name": "Distribution",
                    "description": "Go-to-market and leverage.",
                },
                {
                    "id": "lens-2",
                    "slug": "business-model",
                    "name": "Business Model",
                    "description": "Revenue and monetization.",
                },
            ],
            "claim_lenses": [
                {"claim_id": "claim-1", "lens_id": "lens-1", "weight": 0.91},
                {"claim_id": "claim-2", "lens_id": "lens-1", "weight": 0.78},
                {"claim_id": "claim-3", "lens_id": "lens-2", "weight": 0.86},
                {"claim_id": "claim-4", "lens_id": "lens-2", "weight": 0.74},
            ],
            "claim_links": [
                {
                    "id": "link-1",
                    "from_claim_id": "claim-1",
                    "to_claim_id": "claim-2",
                    "link_type": "leads_to",
                    "confidence": 0.76,
                    "explanation": "Launch creates the competitive effect.",
                    "created_at": "2026-03-20T00:00:00+00:00",
                },
                {
                    "id": "link-2",
                    "from_claim_id": "claim-3",
                    "to_claim_id": "claim-4",
                    "link_type": "contradicts",
                    "confidence": 0.71,
                    "explanation": "The skeptical article disputes the growth framing.",
                    "created_at": "2026-03-27T00:00:00+00:00",
                },
            ],
            "entity_relationships": [
                {
                    "id": "rel-1",
                    "subject_entity_id": "entity-acme",
                    "relation_type": "owns",
                    "object_entity_id": "entity-atlas",
                    "source_id": "source-1",
                    "confidence": 0.93,
                    "valid_from": "2026-03-15T00:00:00+00:00",
                    "valid_to": None,
                    "metadata": {},
                    "created_at": "2026-03-15T00:00:00+00:00",
                },
                {
                    "id": "rel-2",
                    "subject_entity_id": "entity-acme",
                    "relation_type": "competes_with",
                    "object_entity_id": "entity-contoso",
                    "source_id": "source-2",
                    "confidence": 0.78,
                    "valid_from": None,
                    "valid_to": None,
                    "metadata": {},
                    "created_at": "2026-03-20T00:00:00+00:00",
                },
                {
                    "id": "rel-3",
                    "subject_entity_id": "entity-atlas",
                    "relation_type": "participates_in",
                    "object_entity_id": "entity-market",
                    "source_id": "source-1",
                    "confidence": 0.7,
                    "valid_from": None,
                    "valid_to": None,
                    "metadata": {},
                    "created_at": "2026-03-15T00:00:00+00:00",
                },
            ],
        }
    )


def test_get_entity_dossier_returns_timeline_recent_changes_and_relationships():
    db = build_fake_db()

    dossier = get_entity_dossier("entity-acme", db)

    assert dossier["entity"]["canonical_name"] == "Acme"
    assert [claim["id"] for claim in dossier["timeline"]] == ["claim-4", "claim-3", "claim-1"]
    assert dossier["current_thesis"]["top_claims"][0]["id"] == "claim-1"
    assert dossier["recent_changes"]["items"][0]["id"] == "claim-4"
    assert dossier["relationships"][0]["relation_type"] == "owns"
    assert dossier["relationships"][0]["items"][0]["counterparty_entity"]["canonical_name"] == "Atlas"
    assert dossier["timeline"][0]["is_contradictory"] is True
    assert dossier["timeline"][1]["contradiction_count"] == 1


def test_get_entity_dossier_uses_fallback_source_dates_for_object_side_claims():
    db = build_fake_db()

    dossier = get_entity_dossier("entity-contoso", db)

    assert len(dossier["timeline"]) == 1
    assert dossier["timeline"][0]["id"] == "claim-2"
    assert dossier["timeline"][0]["entity_role"] == "object"
    assert dossier["timeline"][0]["timeline_at"] == "2026-03-20T00:00:00+00:00"
    assert dossier["timeline"][0]["counterparty_entity"]["canonical_name"] == "Atlas"


def test_list_entities_aggregates_claim_counts_and_latest_activity():
    db = build_fake_db()

    entities = list_entities(db)

    assert [entity["id"] for entity in entities[:3]] == [
        "entity-acme",
        "entity-atlas",
        "entity-contoso",
    ]
    assert entities[0]["claim_count"] == 3
    assert entities[0]["source_count"] == 3
    assert entities[0]["latest_claim_text"] == "Acme analytics revenue growth is overstated."

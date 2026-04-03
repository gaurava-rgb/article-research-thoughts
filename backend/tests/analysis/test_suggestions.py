"""Tests for Phase 4 gap-aware suggestion heuristics."""

from datetime import datetime, timedelta, timezone

from second_brain.analysis.suggestions import generate_suggestion_candidates


def test_generate_suggestion_candidates_emits_all_phase4_types():
    now = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(days=2)).isoformat()
    very_recent = (now - timedelta(days=1)).isoformat()

    sources = [
        {
            "id": "src-1",
            "title": "OpenClaw launches new platform",
            "published_at": recent,
            "ingested_at": recent,
            "tier": "analysis",
            "kind": "article",
            "source_type": "readwise",
        },
        {
            "id": "src-2",
            "title": "Why OpenClaw matters",
            "published_at": recent,
            "ingested_at": recent,
            "tier": "reporting",
            "kind": "article",
            "source_type": "readwise",
        },
        {
            "id": "src-3",
            "title": "OpenClaw ecosystem reactions",
            "published_at": very_recent,
            "ingested_at": very_recent,
            "tier": "social",
            "kind": "thread",
            "source_type": "readwise",
        },
    ]
    entities = [
        {
            "id": "ent-1",
            "canonical_name": "OpenClaw",
            "entity_type": "company",
            "ticker": None,
            "metadata": {},
        }
    ]
    source_entities = [
        {"source_id": "src-1", "entity_id": "ent-1", "role": "mentioned"},
        {"source_id": "src-2", "entity_id": "ent-1", "role": "mentioned"},
        {"source_id": "src-3", "entity_id": "ent-1", "role": "mentioned"},
    ]
    claims = [
        {
            "id": "claim-1",
            "source_id": "src-1",
            "subject_entity_id": "ent-1",
            "object_entity_id": None,
            "claim_type": "announcement",
            "claim_text": "OpenClaw launched a new platform for enterprise agents.",
            "event_at": very_recent,
            "importance": 0.9,
            "confidence": 0.8,
            "created_at": very_recent,
        },
        {
            "id": "claim-2",
            "source_id": "src-2",
            "subject_entity_id": "ent-1",
            "object_entity_id": None,
            "claim_type": "analysis",
            "claim_text": "OpenClaw could reshape agent deployment for large teams.",
            "event_at": recent,
            "importance": 0.7,
            "confidence": 0.7,
            "created_at": recent,
        },
        {
            "id": "claim-3",
            "source_id": "src-3",
            "subject_entity_id": "ent-1",
            "object_entity_id": None,
            "claim_type": "reaction",
            "claim_text": "Operators are debating whether OpenClaw can sustain momentum.",
            "event_at": recent,
            "importance": 0.6,
            "confidence": 0.6,
            "created_at": recent,
        },
    ]
    claim_links: list[dict] = []
    claim_evidence = [
        {"claim_id": "claim-1"},
        {"claim_id": "claim-1"},
        {"claim_id": "claim-2"},
    ]

    suggestions = generate_suggestion_candidates(
        sources=sources,
        entities=entities,
        source_entities=source_entities,
        claims=claims,
        claim_links=claim_links,
        claim_evidence=claim_evidence,
        now=now,
    )

    suggestion_types = {item["type"] for item in suggestions}
    assert "coverage_gap" in suggestion_types
    assert "counterpoint" in suggestion_types
    assert "follow_up" in suggestion_types
    assert "watch" in suggestion_types

    coverage_gap = next(item for item in suggestions if item["type"] == "coverage_gap")
    assert coverage_gap["metadata"]["entity_name"] == "OpenClaw"
    assert "query" in coverage_gap["metadata"]


def test_generate_suggestion_candidates_skips_entities_without_recent_activity():
    now = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
    stale = (now - timedelta(days=200)).isoformat()

    suggestions = generate_suggestion_candidates(
        sources=[
            {
                "id": "src-1",
                "title": "Old note",
                "published_at": stale,
                "ingested_at": stale,
                "tier": "analysis",
                "kind": "article",
                "source_type": "readwise",
            }
        ],
        entities=[
            {
                "id": "ent-1",
                "canonical_name": "OldCo",
                "entity_type": "company",
                "ticker": None,
                "metadata": {},
            }
        ],
        source_entities=[{"source_id": "src-1", "entity_id": "ent-1", "role": "mentioned"}],
        claims=[],
        claim_links=[],
        claim_evidence=[],
        now=now,
    )

    assert suggestions == []

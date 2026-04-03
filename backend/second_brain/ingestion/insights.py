"""Insights and Phase 4 suggestion helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from second_brain.analysis.suggestions import SUGGESTION_TYPES, generate_suggestion_candidates

EXTENDED_INSIGHT_COLUMNS = (
    "id, type, title, body, seen, created_at, status, summary, metadata, processing_run_id"
)
LEGACY_INSIGHT_COLUMNS = "id, type, title, body, seen, created_at"
SUGGESTION_RUN_TYPE = "research_suggestions"


def _safe_select(db, table_name: str, columns: str) -> list[dict[str, Any]]:
    try:
        data = db.table(table_name).select(columns).execute().data
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _safe_filtered_select(
    db,
    table_name: str,
    columns: str,
    *,
    eq_filters: list[tuple[str, Any]] | None = None,
    in_filters: list[tuple[str, list[Any]]] | None = None,
) -> list[dict[str, Any]]:
    try:
        query = db.table(table_name).select(columns)
        for column, value in eq_filters or []:
            query = query.eq(column, value)
        for column, values in in_filters or []:
            if values:
                query = query.in_(column, values)
        data = query.execute().data
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _normalize_insight(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "body": row["body"],
        "seen": bool(row.get("seen", False)),
        "created_at": row["created_at"],
        "status": row.get("status", "active"),
        "summary": row.get("summary"),
        "metadata": row.get("metadata") or {},
        "processing_run_id": row.get("processing_run_id"),
        "entities": [],
        "claims": [],
    }


def _load_insight_rows(db) -> list[dict[str, Any]]:
    try:
        rows = db.table("insights").select(EXTENDED_INSIGHT_COLUMNS).order("created_at", desc=True).execute().data
    except Exception:
        rows = db.table("insights").select(LEGACY_INSIGHT_COLUMNS).order("created_at", desc=True).execute().data
    rows = rows if isinstance(rows, list) else []
    normalized = [_normalize_insight(row) for row in rows]
    active_rows = [row for row in normalized if row.get("status", "active") != "superseded"]
    return active_rows


def _hydrate_insight_links(db, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    insight_ids = [row["id"] for row in insights]
    if not insight_ids:
        return insights

    insight_entities = _safe_filtered_select(
        db,
        "insight_entities",
        "insight_id, entity_id, role",
        in_filters=[("insight_id", insight_ids)],
    )
    insight_claims = _safe_filtered_select(
        db,
        "insight_claims",
        "insight_id, claim_id, role",
        in_filters=[("insight_id", insight_ids)],
    )

    entity_ids = [row["entity_id"] for row in insight_entities if row.get("entity_id")]
    entities = _safe_filtered_select(
        db,
        "entities",
        "id, canonical_name, entity_type, ticker, metadata",
        in_filters=[("id", entity_ids)],
    )
    entity_lookup = {row["id"]: row for row in entities}

    claim_ids = [row["claim_id"] for row in insight_claims if row.get("claim_id")]
    claims = _safe_filtered_select(
        db,
        "claims",
        "id, claim_text, claim_type, subject_entity_id, object_entity_id, importance, confidence",
        in_filters=[("id", claim_ids)],
    )
    claim_lookup = {row["id"]: row for row in claims}

    linked_entity_ids = [
        entity_id
        for claim in claims
        for entity_id in (claim.get("subject_entity_id"), claim.get("object_entity_id"))
        if entity_id
    ]
    linked_entities = _safe_filtered_select(
        db,
        "entities",
        "id, canonical_name, entity_type, ticker, metadata",
        in_filters=[("id", linked_entity_ids)],
    )
    linked_entity_lookup = {row["id"]: row for row in linked_entities}

    entities_by_insight: dict[str, list[dict[str, Any]]] = {row["id"]: [] for row in insights}
    for relation in insight_entities:
        entity = entity_lookup.get(relation["entity_id"])
        if not entity:
            continue
        entities_by_insight.setdefault(relation["insight_id"], []).append(
            {
                "id": entity["id"],
                "canonical_name": entity["canonical_name"],
                "entity_type": entity["entity_type"],
                "ticker": entity.get("ticker"),
                "metadata": entity.get("metadata") or {},
                "role": relation.get("role"),
            }
        )

    claims_by_insight: dict[str, list[dict[str, Any]]] = {row["id"]: [] for row in insights}
    for relation in insight_claims:
        claim = claim_lookup.get(relation["claim_id"])
        if not claim:
            continue
        subject = linked_entity_lookup.get(claim.get("subject_entity_id"))
        claims_by_insight.setdefault(relation["insight_id"], []).append(
            {
                "id": claim["id"],
                "claim_text": claim["claim_text"],
                "claim_type": claim["claim_type"],
                "importance": claim.get("importance"),
                "confidence": claim.get("confidence"),
                "role": relation.get("role"),
                "subject_entity_name": subject.get("canonical_name") if subject else None,
            }
        )

    for insight in insights:
        insight["entities"] = entities_by_insight.get(insight["id"], [])
        insight["claims"] = claims_by_insight.get(insight["id"], [])
    return insights


def _insert_insight(
    db,
    *,
    insight_type: str,
    title: str,
    body: str,
    summary: str | None = None,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
    processing_run_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "type": insight_type,
        "title": title,
        "body": body,
        "seen": False,
        "status": status,
        "summary": summary,
        "metadata": metadata or {},
        "processing_run_id": processing_run_id,
    }
    try:
        row = db.table("insights").insert(payload).execute().data[0]
    except Exception:
        legacy_payload = {
            "type": insight_type,
            "title": title,
            "body": body,
            "seen": False,
        }
        row = db.table("insights").insert(legacy_payload).execute().data[0]
    return _normalize_insight(row)


def _start_processing_run(db, *, run_type: str) -> str | None:
    try:
        row = db.table("processing_runs").insert(
            {"run_type": run_type, "status": "running", "metadata": {}}
        ).execute().data[0]
        return row["id"]
    except Exception:
        return None


def _finish_processing_run(
    db,
    *,
    run_id: str | None,
    status: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not run_id:
        return
    try:
        db.table("processing_runs").update(
            {
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }
        ).eq("id", run_id).execute()
    except Exception:
        return


def _supersede_existing_suggestions(db) -> None:
    try:
        db.table("insights").update({"status": "superseded"}).in_(
            "type", list(SUGGESTION_TYPES)
        ).eq("status", "active").execute()
        return
    except Exception:
        pass
    try:
        db.table("insights").delete().in_("type", list(SUGGESTION_TYPES)).execute()
    except Exception:
        return


def _link_insight_entities(db, insight_id: str, entity_ids: list[str]) -> None:
    if not entity_ids:
        return
    rows = [
        {"insight_id": insight_id, "entity_id": entity_id, "role": "subject"}
        for entity_id in dict.fromkeys(entity_ids)
    ]
    try:
        db.table("insight_entities").insert(rows).execute()
    except Exception:
        return


def _link_insight_claims(db, insight_id: str, claim_ids: list[str]) -> None:
    if not claim_ids:
        return
    rows = [
        {"insight_id": insight_id, "claim_id": claim_id, "role": "support"}
        for claim_id in dict.fromkeys(claim_ids)
    ]
    try:
        db.table("insight_claims").insert(rows).execute()
    except Exception:
        return


def _load_phase4_rows(db) -> dict[str, list[dict[str, Any]]]:
    return {
        "sources": _safe_select(
            db,
            "sources",
            "id, title, author, url, published_at, ingested_at, kind, tier, publisher, source_type",
        ),
        "entities": _safe_select(
            db,
            "entities",
            "id, canonical_name, entity_type, ticker, metadata",
        ),
        "source_entities": _safe_select(
            db,
            "source_entities",
            "source_id, entity_id, role, mention_count, salience",
        ),
        "claims": _safe_select(
            db,
            "claims",
            (
                "id, source_id, subject_entity_id, object_entity_id, claim_type, modality, stance, "
                "claim_text, normalized_claim, event_at, confidence, importance, metadata, created_at"
            ),
        ),
        "claim_links": _safe_select(
            db,
            "claim_links",
            "id, from_claim_id, to_claim_id, link_type, confidence, explanation, created_at",
        ),
        "claim_evidence": _safe_select(
            db,
            "claim_evidence",
            "id, claim_id, source_id, chunk_id, evidence_text, start_char, end_char, confidence, created_at",
        ),
    }


def generate_digest(db, llm_provider) -> dict | None:
    """Generate a weekly digest from sources ingested in the last 7 days."""

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    sources = (
        db.table("sources")
        .select("id, title, author, published_at, ingested_at")
        .gte("ingested_at", cutoff)
        .order("ingested_at", desc=True)
        .execute()
        .data
    ) or []

    if not sources:
        return None

    source_ids = [s["id"] for s in sources]
    memberships = (
        db.table("source_topics")
        .select("source_id, topics(id, name)")
        .in_("source_id", source_ids)
        .execute()
        .data
    ) or []

    source_to_topic: dict[str, str] = {}
    for membership in memberships:
        topic = membership.get("topics")
        if topic:
            source_to_topic[membership["source_id"]] = topic["name"]

    topic_articles: dict[str, list[str]] = {}
    for source in sources:
        topic_name = source_to_topic.get(source["id"], "Uncategorized")
        topic_articles.setdefault(topic_name, []).append(source["title"])

    lines = [f"Articles saved in the last 7 days ({len(sources)} total):\n"]
    for topic_name, titles in sorted(topic_articles.items(), key=lambda item: -len(item[1]))[:10]:
        lines.append(f"**{topic_name}** ({len(titles)} article{'s' if len(titles) != 1 else ''}):")
        for title in titles[:8]:
            lines.append(f"  - {title}")
        lines.append("")

    context = "\n".join(lines)
    summary = llm_provider.complete(
        [
            {
                "role": "system",
                "content": (
                    "You write weekly reading digests for a personal knowledge base. "
                    "Synthesize the themes that emerged from the user's reading — "
                    "don't just list articles. Write 3–5 short paragraphs covering "
                    "the main themes, what's interesting about them, and any patterns. "
                    "Be specific: mention article topics and subject areas. 200–300 words."
                ),
            },
            {
                "role": "user",
                "content": f"Here's what I've been reading this week. Write my digest:\n\n{context}",
            },
        ]
    )

    title = f"Weekly Digest — {datetime.now().strftime('%B %d, %Y')}"
    return _insert_insight(
        db,
        insight_type="digest",
        title=title,
        body=summary,
        summary="Weekly reading digest",
        metadata={"source_count": len(sources), "topic_count": len(topic_articles)},
    )


def generate_suggestions(db) -> list[dict[str, Any]]:
    """Generate evidence-backed Phase 4 suggestions from stored analyst primitives."""

    run_id = _start_processing_run(db, run_type=SUGGESTION_RUN_TYPE)
    try:
        rows = _load_phase4_rows(db)
        suggestions = generate_suggestion_candidates(**rows)
        if not suggestions:
            _finish_processing_run(
                db,
                run_id=run_id,
                status="completed",
                metadata={"suggestion_count": 0, "types": {}},
            )
            return []

        _supersede_existing_suggestions(db)

        created: list[dict[str, Any]] = []
        for suggestion in suggestions:
            row = _insert_insight(
                db,
                insight_type=suggestion["type"],
                title=suggestion["title"],
                body=suggestion["body"],
                summary=suggestion.get("summary"),
                status="active",
                metadata=suggestion.get("metadata"),
                processing_run_id=run_id,
            )
            _link_insight_entities(db, row["id"], suggestion.get("entity_ids", []))
            _link_insight_claims(db, row["id"], suggestion.get("claim_ids", []))
            row["entities"] = [
                {
                    "id": entity["id"],
                    "canonical_name": entity["canonical_name"],
                    "entity_type": entity["entity_type"],
                    "ticker": entity.get("ticker"),
                    "metadata": entity.get("metadata") or {},
                    "role": "subject",
                }
                for entity in rows["entities"]
                if entity["id"] in set(suggestion.get("entity_ids", []))
            ]
            row["claims"] = [
                {
                    "id": claim["id"],
                    "claim_text": claim["claim_text"],
                    "claim_type": claim["claim_type"],
                    "importance": claim.get("importance"),
                    "confidence": claim.get("confidence"),
                    "role": "support",
                    "subject_entity_name": None,
                }
                for claim in rows["claims"]
                if claim["id"] in set(suggestion.get("claim_ids", []))
            ]
            created.append(row)

        counts = Counter(item["type"] for item in created)
        _finish_processing_run(
            db,
            run_id=run_id,
            status="completed",
            metadata={"suggestion_count": len(created), "types": dict(counts)},
        )
        return created
    except Exception as exc:
        _finish_processing_run(
            db,
            run_id=run_id,
            status="failed",
            metadata={"error": str(exc)},
        )
        raise


def get_insights(db) -> dict:
    """Return all active insights ordered newest-first, plus unseen count."""

    rows = _load_insight_rows(db)
    rows = _hydrate_insight_links(db, rows)
    unseen_count = sum(1 for row in rows if not row.get("seen", True))
    return {"insights": rows, "unseen_count": unseen_count}


def mark_seen(db, insight_id: str) -> None:
    """Mark a single insight as seen."""

    db.table("insights").update({"seen": True}).eq("id", insight_id).execute()

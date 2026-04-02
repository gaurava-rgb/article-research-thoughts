"""Phase 3 entity dossier and timeline helpers."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import supabase


SUPPORTED_RELATION_TYPES = (
    "owns",
    "competes_with",
    "participates_in",
    "depends_on",
)
RECENT_WINDOW_DAYS = 90


def _parse_timestamp(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            return dt.datetime.fromisoformat(text).replace(tzinfo=dt.UTC)
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed


def _sort_timestamp_key(value: Any) -> tuple[bool, dt.datetime]:
    parsed = _parse_timestamp(value)
    return (parsed is not None, parsed or dt.datetime.min.replace(tzinfo=dt.UTC))


def _timeline_sort_key(row: dict[str, Any]) -> tuple[bool, dt.datetime, float, str]:
    return (
        *_sort_timestamp_key(row.get("timeline_at")),
        row.get("importance") or 0.0,
        row.get("claim_id") or "",
    )


def _claim_sort_key(row: dict[str, Any]) -> tuple[float, bool, dt.datetime, str]:
    return (
        row.get("importance") or 0.0,
        *_sort_timestamp_key(row.get("timeline_at")),
        row.get("id") or "",
    )


def _safe_select(
    db: "supabase.Client",
    table_name: str,
    columns: str,
) -> list[dict[str, Any]]:
    try:
        return db.table(table_name).select(columns).execute().data or []
    except Exception:
        return []


def _safe_filtered_select(
    db: "supabase.Client",
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
            query = query.in_(column, values)
        return query.execute().data or []
    except Exception:
        return []


def _load_entities(
    db: "supabase.Client",
    entity_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not entity_ids:
        return {}

    unique_ids = list(dict.fromkeys(entity_ids))
    entity_rows = _safe_filtered_select(
        db,
        "entities",
        "id, canonical_name, entity_type, ticker, metadata",
        in_filters=[("id", unique_ids)],
    )
    alias_rows = _safe_filtered_select(
        db,
        "entity_aliases",
        "entity_id, alias, alias_type, confidence",
        in_filters=[("entity_id", unique_ids)],
    )
    aliases_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for alias in alias_rows:
        aliases_by_entity[alias["entity_id"]].append(alias)

    return {
        entity["id"]: {
            **entity,
            "metadata": entity.get("metadata") or {},
            "aliases": aliases_by_entity.get(entity["id"], []),
        }
        for entity in entity_rows
    }


def _load_sources(
    db: "supabase.Client",
    source_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not source_ids:
        return {}

    unique_ids = list(dict.fromkeys(source_ids))
    rows = _safe_filtered_select(
        db,
        "sources",
        "id, title, url, source_type, kind, tier, published_at, ingested_at",
        in_filters=[("id", unique_ids)],
    )
    return {row["id"]: row for row in rows}


def _build_entity_claim_timeline(entity_id: str, db: "supabase.Client") -> list[dict[str, Any]]:
    claims = _safe_select(
        db,
        "claims",
        (
            "id, source_id, subject_entity_id, object_entity_id, claim_type, modality, stance, "
            "claim_text, normalized_claim, event_at, confidence, importance, created_at"
        ),
    )
    relevant_claims = [
        claim
        for claim in claims
        if claim.get("subject_entity_id") == entity_id or claim.get("object_entity_id") == entity_id
    ]
    if not relevant_claims:
        return []

    entity_lookup = _load_entities(
        db,
        [
            related_id
            for claim in relevant_claims
            for related_id in (claim.get("subject_entity_id"), claim.get("object_entity_id"))
            if related_id
        ],
    )
    source_lookup = _load_sources(
        db,
        [claim["source_id"] for claim in relevant_claims if claim.get("source_id")],
    )

    rows: list[dict[str, Any]] = []
    for claim in relevant_claims:
        source = source_lookup.get(claim["source_id"], {})
        if claim.get("subject_entity_id") == entity_id:
            counterparty_id = claim.get("object_entity_id")
            counterparty = entity_lookup.get(counterparty_id) if counterparty_id else None
            entity = entity_lookup.get(entity_id)
            rows.append(
                {
                    "claim_id": claim["id"],
                    "entity_id": entity_id,
                    "entity_name": entity.get("canonical_name") if entity else None,
                    "entity_role": "subject",
                    "counterparty_entity_id": counterparty_id,
                    "counterparty_entity_name": (
                        counterparty.get("canonical_name") if counterparty else None
                    ),
                    "claim_type": claim["claim_type"],
                    "modality": claim["modality"],
                    "stance": claim.get("stance"),
                    "claim_text": claim["claim_text"],
                    "normalized_claim": claim.get("normalized_claim"),
                    "event_at": claim.get("event_at"),
                    "importance": claim.get("importance"),
                    "confidence": claim.get("confidence"),
                    "timeline_at": (
                        claim.get("event_at")
                        or source.get("published_at")
                        or source.get("ingested_at")
                        or claim.get("created_at")
                    ),
                    "source_id": source.get("id"),
                    "source_title": source.get("title"),
                    "source_url": source.get("url"),
                    "source_type": source.get("source_type"),
                    "source_kind": source.get("kind"),
                    "source_tier": source.get("tier"),
                    "source_published_at": source.get("published_at"),
                    "source_ingested_at": source.get("ingested_at"),
                }
            )
        if claim.get("object_entity_id") == entity_id:
            counterparty_id = claim.get("subject_entity_id")
            counterparty = entity_lookup.get(counterparty_id) if counterparty_id else None
            entity = entity_lookup.get(entity_id)
            rows.append(
                {
                    "claim_id": claim["id"],
                    "entity_id": entity_id,
                    "entity_name": entity.get("canonical_name") if entity else None,
                    "entity_role": "object",
                    "counterparty_entity_id": counterparty_id,
                    "counterparty_entity_name": (
                        counterparty.get("canonical_name") if counterparty else None
                    ),
                    "claim_type": claim["claim_type"],
                    "modality": claim["modality"],
                    "stance": claim.get("stance"),
                    "claim_text": claim["claim_text"],
                    "normalized_claim": claim.get("normalized_claim"),
                    "event_at": claim.get("event_at"),
                    "importance": claim.get("importance"),
                    "confidence": claim.get("confidence"),
                    "timeline_at": (
                        claim.get("event_at")
                        or source.get("published_at")
                        or source.get("ingested_at")
                        or claim.get("created_at")
                    ),
                    "source_id": source.get("id"),
                    "source_title": source.get("title"),
                    "source_url": source.get("url"),
                    "source_type": source.get("source_type"),
                    "source_kind": source.get("kind"),
                    "source_tier": source.get("tier"),
                    "source_published_at": source.get("published_at"),
                    "source_ingested_at": source.get("ingested_at"),
                }
            )

    return rows


def _load_timeline_rows(entity_id: str, db: "supabase.Client") -> list[dict[str, Any]]:
    try:
        rows = (
            db.table("entity_claim_timeline")
            .select(
                (
                    "claim_id, entity_id, entity_name, entity_role, counterparty_entity_id, "
                    "counterparty_entity_name, claim_type, modality, stance, claim_text, "
                    "normalized_claim, event_at, importance, confidence, timeline_at, source_id, "
                    "source_title, source_url, source_type, source_kind, source_tier, "
                    "source_published_at, source_ingested_at"
                )
            )
            .eq("entity_id", entity_id)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []
    return rows if rows else _build_entity_claim_timeline(entity_id, db)


def _load_claim_details(
    db: "supabase.Client",
    claim_ids: list[str],
    timeline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not claim_ids:
        return []

    claims = _safe_filtered_select(
        db,
        "claims",
        (
            "id, source_id, subject_entity_id, object_entity_id, claim_type, modality, stance, "
            "claim_text, normalized_claim, event_at, event_end_at, confidence, importance, "
            "extraction_run_id, metadata, created_at"
        ),
        in_filters=[("id", claim_ids)],
    )
    claim_lookup = {claim["id"]: claim for claim in claims}
    evidence_rows = _safe_filtered_select(
        db,
        "claim_evidence",
        "id, claim_id, source_id, chunk_id, evidence_text, start_char, end_char, confidence, created_at",
        in_filters=[("claim_id", claim_ids)],
    )
    claim_lens_rows = _safe_filtered_select(
        db,
        "claim_lenses",
        "claim_id, lens_id, weight",
        in_filters=[("claim_id", claim_ids)],
    )
    outgoing_links = _safe_filtered_select(
        db,
        "claim_links",
        "id, from_claim_id, to_claim_id, link_type, confidence, explanation, created_at",
        in_filters=[("from_claim_id", claim_ids)],
    )
    incoming_links = _safe_filtered_select(
        db,
        "claim_links",
        "id, from_claim_id, to_claim_id, link_type, confidence, explanation, created_at",
        in_filters=[("to_claim_id", claim_ids)],
    )
    all_links = {link["id"]: link for link in outgoing_links + incoming_links}

    linked_claim_ids = list(
        {
            related_id
            for link in all_links.values()
            for related_id in (link.get("from_claim_id"), link.get("to_claim_id"))
            if related_id
        }
    )
    linked_claim_rows = _safe_filtered_select(
        db,
        "claims",
        "id, claim_text",
        in_filters=[("id", linked_claim_ids)],
    )
    linked_claim_lookup = {claim["id"]: claim for claim in linked_claim_rows}

    chunk_ids = [row["chunk_id"] for row in evidence_rows if row.get("chunk_id")]
    chunk_lookup = {
        row["id"]: row
        for row in _safe_filtered_select(
            db,
            "chunks",
            "id, chunk_index",
            in_filters=[("id", chunk_ids)],
        )
    }
    lens_lookup = {
        lens["id"]: lens
        for lens in _safe_select(db, "lenses", "id, slug, name, description")
    }
    entity_lookup = _load_entities(
        db,
        [
            entity_id
            for claim in claims
            for entity_id in (claim.get("subject_entity_id"), claim.get("object_entity_id"))
            if entity_id
        ],
    )

    evidence_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for evidence in evidence_rows:
        chunk = chunk_lookup.get(evidence.get("chunk_id"))
        evidence_by_claim[evidence["claim_id"]].append(
            {
                **evidence,
                "chunk_index": chunk.get("chunk_index") if chunk else None,
            }
        )

    lenses_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim_lens in claim_lens_rows:
        lens = lens_lookup.get(claim_lens["lens_id"])
        if not lens:
            continue
        lenses_by_claim[claim_lens["claim_id"]].append(
            {
                "id": lens["id"],
                "slug": lens["slug"],
                "name": lens["name"],
                "description": lens.get("description"),
                "weight": claim_lens.get("weight"),
            }
        )

    links_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    contradiction_map: dict[str, set[str]] = defaultdict(set)
    for link in all_links.values():
        if link["from_claim_id"] in claim_lookup:
            related_claim_id = link["to_claim_id"]
            direction = "outgoing"
            owner_claim_id = link["from_claim_id"]
        else:
            related_claim_id = link["from_claim_id"]
            direction = "incoming"
            owner_claim_id = link["to_claim_id"]

        related_claim = linked_claim_lookup.get(related_claim_id)
        if link["link_type"] == "contradicts":
            contradiction_map[owner_claim_id].add(related_claim_id)

        links_by_claim[owner_claim_id].append(
            {
                "id": link["id"],
                "direction": direction,
                "link_type": link["link_type"],
                "confidence": link.get("confidence"),
                "explanation": link.get("explanation"),
                "created_at": link["created_at"],
                "related_claim_id": related_claim_id,
                "related_claim_text": related_claim.get("claim_text") if related_claim else None,
            }
        )

    normalized_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        normalized_claim = (claim.get("normalized_claim") or "").strip().lower()
        if normalized_claim:
            normalized_groups[normalized_claim].append(claim)
    for grouped_claims in normalized_groups.values():
        stances = {
            claim.get("stance")
            for claim in grouped_claims
            if claim.get("stance") not in (None, "")
        }
        if len(stances) <= 1:
            continue
        grouped_ids = [claim["id"] for claim in grouped_claims]
        for claim_id in grouped_ids:
            contradiction_map[claim_id].update(other_id for other_id in grouped_ids if other_id != claim_id)

    timeline_by_claim = {row["claim_id"]: row for row in timeline_rows}
    payloads = []
    for claim in claims:
        timeline_row = timeline_by_claim.get(claim["id"], {})
        contradictions = contradiction_map.get(claim["id"], set())
        payloads.append(
            {
                **claim,
                "metadata": claim.get("metadata") or {},
                "timeline_at": timeline_row.get("timeline_at"),
                "entity_role": timeline_row.get("entity_role"),
                "counterparty_entity": (
                    entity_lookup.get(timeline_row["counterparty_entity_id"])
                    if timeline_row.get("counterparty_entity_id")
                    else None
                ),
                "source": {
                    "id": timeline_row.get("source_id"),
                    "title": timeline_row.get("source_title"),
                    "url": timeline_row.get("source_url"),
                    "source_type": timeline_row.get("source_type"),
                    "kind": timeline_row.get("source_kind"),
                    "tier": timeline_row.get("source_tier"),
                    "published_at": timeline_row.get("source_published_at"),
                    "ingested_at": timeline_row.get("source_ingested_at"),
                },
                "subject_entity": entity_lookup.get(claim.get("subject_entity_id")),
                "object_entity": entity_lookup.get(claim.get("object_entity_id")),
                "evidence": evidence_by_claim.get(claim["id"], []),
                "lenses": sorted(
                    lenses_by_claim.get(claim["id"], []),
                    key=lambda lens: (lens.get("weight") or 0, lens["name"]),
                    reverse=True,
                ),
                "links": sorted(
                    links_by_claim.get(claim["id"], []),
                    key=lambda link: (
                        link["direction"] != "outgoing",
                        link.get("confidence") or 0,
                        link["link_type"],
                    ),
                    reverse=True,
                ),
                "is_contradictory": bool(contradictions),
                "contradiction_count": len(contradictions),
            }
        )

    return sorted(payloads, key=_claim_sort_key, reverse=True)


def _build_current_thesis(entity: dict[str, Any], timeline: list[dict[str, Any]]) -> dict[str, Any]:
    source_count = len({claim["source"]["id"] for claim in timeline if claim.get("source", {}).get("id")})
    top_claims = sorted(timeline, key=_claim_sort_key, reverse=True)[:3]
    lens_counts = Counter(
        lens["name"]
        for claim in timeline
        for lens in claim.get("lenses", [])
    )
    claim_type_counts = Counter(claim["claim_type"] for claim in timeline)

    if not timeline:
        summary = f"No structured claims have been stored for {entity['canonical_name']} yet."
    else:
        lens_summary = ", ".join(name for name, _count in lens_counts.most_common(3))
        claim_type_summary = ", ".join(
            claim_type.replace("-", " ") for claim_type, _count in claim_type_counts.most_common(3)
        )
        strongest_themes = lens_summary or claim_type_summary or "stored claims"
        latest_claim = top_claims[0]["claim_text"] if top_claims else "No recent claim available."
        summary = (
            f"{entity['canonical_name']} has {len(timeline)} tracked claims across {source_count} "
            f"source{'s' if source_count != 1 else ''}. Strongest themes: {strongest_themes}. "
            f"Latest tracked claim: {latest_claim}"
        )

    return {
        "summary": summary,
        "source_count": source_count,
        "claim_count": len(timeline),
        "top_claims": top_claims,
        "dominant_lenses": [
            {"name": name, "count": count}
            for name, count in lens_counts.most_common(5)
        ],
        "claim_type_breakdown": [
            {"claim_type": claim_type, "count": count}
            for claim_type, count in claim_type_counts.most_common(5)
        ],
    }


def _build_recent_changes(entity: dict[str, Any], timeline: list[dict[str, Any]]) -> dict[str, Any]:
    if not timeline:
        return {
            "summary": f"No dated changes are stored for {entity['canonical_name']} yet.",
            "window_days": RECENT_WINDOW_DAYS,
            "items": [],
        }

    sorted_timeline = sorted(timeline, key=_timeline_sort_key, reverse=True)
    latest_dt = _parse_timestamp(sorted_timeline[0].get("timeline_at"))
    if latest_dt is not None:
        window_start = latest_dt - dt.timedelta(days=RECENT_WINDOW_DAYS)
        recent_items = [
            claim
            for claim in sorted_timeline
            if (_parse_timestamp(claim.get("timeline_at")) or dt.datetime.min.replace(tzinfo=dt.UTC))
            >= window_start
        ]
    else:
        recent_items = []

    if not recent_items:
        recent_items = sorted_timeline[:5]
    else:
        recent_items = recent_items[:5]

    summary = (
        f"{len(recent_items)} recent change{'s' if len(recent_items) != 1 else ''} "
        f"tracked for {entity['canonical_name']} over the last {RECENT_WINDOW_DAYS} days."
    )
    return {
        "summary": summary,
        "window_days": RECENT_WINDOW_DAYS,
        "items": recent_items,
    }


def _load_relationship_groups(entity_id: str, db: "supabase.Client") -> list[dict[str, Any]]:
    rows = _safe_select(
        db,
        "entity_relationships",
        (
            "id, subject_entity_id, relation_type, object_entity_id, source_id, confidence, "
            "valid_from, valid_to, metadata, created_at"
        ),
    )
    relevant = [
        row
        for row in rows
        if row.get("relation_type") in SUPPORTED_RELATION_TYPES
        and (
            row.get("subject_entity_id") == entity_id or row.get("object_entity_id") == entity_id
        )
    ]
    if not relevant:
        return []

    entity_lookup = _load_entities(
        db,
        [
            related_id
            for row in relevant
            for related_id in (row.get("subject_entity_id"), row.get("object_entity_id"))
            if related_id
        ],
    )
    source_lookup = _load_sources(
        db,
        [row["source_id"] for row in relevant if row.get("source_id")],
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in relevant:
        is_outgoing = row.get("subject_entity_id") == entity_id
        counterparty_id = row.get("object_entity_id") if is_outgoing else row.get("subject_entity_id")
        grouped[row["relation_type"]].append(
            {
                "id": row["id"],
                "direction": "outgoing" if is_outgoing else "incoming",
                "relation_type": row["relation_type"],
                "confidence": row.get("confidence"),
                "valid_from": row.get("valid_from"),
                "valid_to": row.get("valid_to"),
                "metadata": row.get("metadata") or {},
                "created_at": row["created_at"],
                "counterparty_entity": (
                    entity_lookup.get(counterparty_id) if counterparty_id else None
                ),
                "source": source_lookup.get(row["source_id"]) if row.get("source_id") else None,
            }
        )

    groups = []
    for relation_type in SUPPORTED_RELATION_TYPES:
        items = grouped.get(relation_type, [])
        if not items:
            continue
        items.sort(
            key=lambda item: (
                item["direction"] != "outgoing",
                (item.get("counterparty_entity") or {}).get("canonical_name") or "",
            )
        )
        groups.append(
            {
                "relation_type": relation_type,
                "label": relation_type.replace("_", " "),
                "items": items,
            }
        )
    return groups


def list_entities(
    db: "supabase.Client",
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    entities = _safe_select(
        db,
        "entities",
        "id, canonical_name, entity_type, ticker, metadata",
    )
    if not entities:
        return []

    alias_rows = _safe_select(db, "entity_aliases", "entity_id, alias")
    aliases_by_entity: dict[str, list[str]] = defaultdict(list)
    for alias in alias_rows:
        aliases_by_entity[alias["entity_id"]].append(alias["alias"])

    source_entities = _safe_select(db, "source_entities", "entity_id, source_id")
    source_ids_by_entity: dict[str, set[str]] = defaultdict(set)
    for row in source_entities:
        source_ids_by_entity[row["entity_id"]].add(row["source_id"])

    claims = _safe_select(
        db,
        "claims",
        "id, source_id, subject_entity_id, object_entity_id, claim_text, event_at, created_at",
    )
    source_lookup = _load_sources(
        db,
        [claim["source_id"] for claim in claims if claim.get("source_id")],
    )

    claim_ids_by_entity: dict[str, set[str]] = defaultdict(set)
    latest_claim_by_entity: dict[str, tuple[tuple[bool, dt.datetime], str, str | None]] = {}
    for claim in claims:
        timeline_at = (
            claim.get("event_at")
            or source_lookup.get(claim["source_id"], {}).get("published_at")
            or source_lookup.get(claim["source_id"], {}).get("ingested_at")
            or claim.get("created_at")
        )
        sort_key = _sort_timestamp_key(timeline_at)
        for entity_id in (claim.get("subject_entity_id"), claim.get("object_entity_id")):
            if not entity_id:
                continue
            claim_ids_by_entity[entity_id].add(claim["id"])
            current = latest_claim_by_entity.get(entity_id)
            if current is None or sort_key > current[0]:
                latest_claim_by_entity[entity_id] = (
                    sort_key,
                    claim["claim_text"],
                    timeline_at,
                )

    results = []
    for entity in entities:
        claim_count = len(claim_ids_by_entity.get(entity["id"], set()))
        source_count = len(source_ids_by_entity.get(entity["id"], set()))
        if claim_count == 0 and source_count == 0:
            continue
        latest = latest_claim_by_entity.get(entity["id"])
        results.append(
            {
                "id": entity["id"],
                "canonical_name": entity["canonical_name"],
                "entity_type": entity["entity_type"],
                "ticker": entity.get("ticker"),
                "metadata": entity.get("metadata") or {},
                "aliases": aliases_by_entity.get(entity["id"], []),
                "alias_count": len(aliases_by_entity.get(entity["id"], [])),
                "source_count": source_count,
                "claim_count": claim_count,
                "latest_timeline_at": latest[2] if latest else None,
                "latest_claim_text": latest[1] if latest else None,
            }
        )

    results.sort(
        key=lambda entity: (
            *_sort_timestamp_key(entity.get("latest_timeline_at")),
            entity["claim_count"],
            entity["canonical_name"].lower(),
        ),
        reverse=True,
    )
    return results[:limit]


def get_entity_dossier(entity_id: str, db: "supabase.Client") -> dict[str, Any]:
    entity_lookup = _load_entities(db, [entity_id])
    entity = entity_lookup.get(entity_id)
    if entity is None:
        raise ValueError(f"Entity {entity_id} not found")

    timeline_rows = sorted(_load_timeline_rows(entity_id, db), key=_timeline_sort_key, reverse=True)
    timeline = _load_claim_details(
        db,
        list(dict.fromkeys(row["claim_id"] for row in timeline_rows)),
        timeline_rows,
    )
    relationship_groups = _load_relationship_groups(entity_id, db)

    return {
        "entity": entity,
        "current_thesis": _build_current_thesis(entity, timeline),
        "recent_changes": _build_recent_changes(entity, timeline),
        "relationships": relationship_groups,
        "timeline": sorted(timeline, key=_timeline_sort_key, reverse=True),
    }

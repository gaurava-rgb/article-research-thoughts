"""Phase 4 gap-aware suggestion heuristics."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Any

SUGGESTION_TYPES = ("coverage_gap", "counterpoint", "follow_up", "watch")

RECENT_SOURCE_WINDOW_DAYS = 45
FOLLOW_UP_WINDOW_DAYS = 14
WATCH_WINDOW_DAYS = 30
MAX_SUGGESTIONS = 8
PRIMARY_TIERS = {"primary"}

TYPE_PRIORITY = {
    "coverage_gap": 4,
    "follow_up": 3,
    "counterpoint": 2,
    "watch": 1,
}


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _parse_timestamp(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            parsed = dt.datetime.fromisoformat(text).replace(tzinfo=dt.UTC)
        else:
            parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed


def _claim_time(claim: dict[str, Any], source_lookup: dict[str, dict[str, Any]]) -> dt.datetime | None:
    source = source_lookup.get(claim.get("source_id"), {})
    for key in ("event_at", "created_at"):
        parsed = _parse_timestamp(claim.get(key))
        if parsed:
            return parsed
    for key in ("published_at", "ingested_at"):
        parsed = _parse_timestamp(source.get(key))
        if parsed:
            return parsed
    return None


def _source_time(source: dict[str, Any]) -> dt.datetime | None:
    for key in ("published_at", "ingested_at", "updated_at"):
        parsed = _parse_timestamp(source.get(key))
        if parsed:
            return parsed
    return None


def _truncate(text: str | None, limit: int = 140) -> str | None:
    if not text:
        return text
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}…"


def _entity_query_hint(entity: dict[str, Any], kind: str) -> str:
    name = entity.get("canonical_name") or "this topic"
    entity_type = entity.get("entity_type") or ""
    if kind == "coverage_gap":
        if entity_type in {"company", "organization"}:
            return f'{name} investor relations earnings call official blog filing'
        return f'{name} official documentation primary source'
    if kind == "counterpoint":
        return f'{name} criticism competitor regulator antitrust skeptical analysis'
    if kind == "follow_up":
        return f'{name} latest update follow-up official announcement'
    return f'{name} latest news official updates'


def _tier_breakdown(sources: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter((source.get("tier") or "unknown") for source in sources)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def generate_suggestion_candidates(
    *,
    sources: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    source_entities: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    claim_links: list[dict[str, Any]],
    claim_evidence: list[dict[str, Any]] | None = None,
    now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """Return ranked suggestion candidates derived from stored analyst primitives."""

    now = now or _now_utc()
    recent_cutoff = now - dt.timedelta(days=RECENT_SOURCE_WINDOW_DAYS)
    follow_up_cutoff = now - dt.timedelta(days=FOLLOW_UP_WINDOW_DAYS)
    watch_cutoff = now - dt.timedelta(days=WATCH_WINDOW_DAYS)

    source_lookup = {source["id"]: source for source in sources if source.get("id")}
    entity_lookup = {entity["id"]: entity for entity in entities if entity.get("id")}
    evidence_count_by_claim = Counter(
        row["claim_id"] for row in (claim_evidence or []) if row.get("claim_id")
    )

    entity_source_ids: dict[str, set[str]] = defaultdict(set)
    for row in source_entities:
        entity_id = row.get("entity_id")
        source_id = row.get("source_id")
        if entity_id and source_id:
            entity_source_ids[entity_id].add(source_id)

    entity_claims: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        for entity_id in (claim.get("subject_entity_id"), claim.get("object_entity_id")):
            if not entity_id:
                continue
            entity_claims[entity_id].append(claim)
            source_id = claim.get("source_id")
            if source_id:
                entity_source_ids[entity_id].add(source_id)

    contradiction_links_by_claim: dict[str, int] = Counter()
    all_links_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in claim_links:
        from_claim_id = link.get("from_claim_id")
        to_claim_id = link.get("to_claim_id")
        if from_claim_id:
            all_links_by_claim[from_claim_id].append(link)
            if link.get("link_type") == "contradicts":
                contradiction_links_by_claim[from_claim_id] += 1
        if to_claim_id:
            all_links_by_claim[to_claim_id].append(link)
            if link.get("link_type") == "contradicts":
                contradiction_links_by_claim[to_claim_id] += 1

    suggestions: list[dict[str, Any]] = []
    for entity_id, source_ids in entity_source_ids.items():
        entity = entity_lookup.get(entity_id)
        if not entity:
            continue

        entity_sources = [source_lookup[sid] for sid in source_ids if sid in source_lookup]
        recent_sources = [
            source for source in entity_sources
            if (_source_time(source) or dt.datetime.min.replace(tzinfo=dt.UTC)) >= recent_cutoff
        ]
        watch_sources = [
            source for source in entity_sources
            if (_source_time(source) or dt.datetime.min.replace(tzinfo=dt.UTC)) >= watch_cutoff
        ]
        if not recent_sources:
            continue

        relevant_claims = entity_claims.get(entity_id, [])
        recent_claims = [
            claim for claim in relevant_claims
            if (_claim_time(claim, source_lookup) or dt.datetime.min.replace(tzinfo=dt.UTC)) >= recent_cutoff
        ]
        watch_claims = [
            claim for claim in relevant_claims
            if (_claim_time(claim, source_lookup) or dt.datetime.min.replace(tzinfo=dt.UTC)) >= watch_cutoff
        ]

        recent_primary_sources = [
            source for source in recent_sources if (source.get("tier") or "").lower() in PRIMARY_TIERS
        ]
        tier_breakdown = _tier_breakdown(recent_sources)
        entity_name = entity.get("canonical_name") or "Unknown entity"

        ranked_claims = sorted(
            recent_claims,
            key=lambda claim: (
                claim.get("importance") or 0.0,
                _claim_time(claim, source_lookup) or dt.datetime.min.replace(tzinfo=dt.UTC),
                claim.get("id") or "",
            ),
            reverse=True,
        )
        top_claim = ranked_claims[0] if ranked_claims else None
        contradiction_count = sum(contradiction_links_by_claim[claim["id"]] for claim in recent_claims if claim.get("id"))

        if len(recent_sources) >= 2 and not recent_primary_sources:
            source_titles = [_truncate(source.get("title"), 80) for source in recent_sources[:3] if source.get("title")]
            reason = (
                f"{entity_name} has {len(recent_sources)} recent saved source"
                f"{'' if len(recent_sources) == 1 else 's'} but none are tiered as primary."
            )
            suggestions.append(
                {
                    "type": "coverage_gap",
                    "title": f"Find a primary source for {entity_name}",
                    "summary": reason,
                    "body": (
                        f"{reason} Validate the current thesis with an official source such as an earnings call, "
                        f"investor relations update, product post, filing, or documentation set."
                    ),
                    "entity_ids": [entity_id],
                    "claim_ids": [claim["id"] for claim in ranked_claims[:3] if claim.get("id")],
                    "metadata": {
                        "reason": reason,
                        "gap_kind": "primary_source",
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "entity_type": entity.get("entity_type"),
                        "query": _entity_query_hint(entity, "coverage_gap"),
                        "recent_source_count": len(recent_sources),
                        "recent_claim_count": len(recent_claims),
                        "tier_breakdown": tier_breakdown,
                        "recent_source_titles": source_titles,
                    },
                    "score": 100 + len(recent_sources) * 10 + len(recent_claims),
                }
            )

        if len(recent_claims) >= 2 and contradiction_count == 0 and top_claim:
            reason = (
                f"{entity_name} has {len(recent_claims)} recent claims but no contradiction links tying in a dissenting view."
            )
            suggestions.append(
                {
                    "type": "counterpoint",
                    "title": f"Pressure-test the {entity_name} thesis",
                    "summary": reason,
                    "body": (
                        f"{reason} Look for a skeptical operator view, a competitor response, or a regulator / market "
                        f"angle to test whether the current reading is one-sided."
                    ),
                    "entity_ids": [entity_id],
                    "claim_ids": [claim["id"] for claim in ranked_claims[:3] if claim.get("id")],
                    "metadata": {
                        "reason": reason,
                        "gap_kind": "counterpoint",
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "entity_type": entity.get("entity_type"),
                        "query": _entity_query_hint(entity, "counterpoint"),
                        "recent_claim_count": len(recent_claims),
                        "contradiction_count": contradiction_count,
                        "trigger_claim_text": _truncate(top_claim.get("claim_text")),
                    },
                    "score": 80 + len(recent_claims) * 8 + int((top_claim.get("importance") or 0) * 10),
                }
            )

        if top_claim:
            top_claim_time = _claim_time(top_claim, source_lookup)
            top_claim_links = all_links_by_claim.get(top_claim.get("id"), [])
            if top_claim_time and top_claim_time >= follow_up_cutoff and not top_claim_links:
                reason = (
                    f"A recent claim about {entity_name} has not been linked to any downstream support, contradiction, or consequence yet."
                )
                suggestions.append(
                    {
                        "type": "follow_up",
                        "title": f"Follow up on {entity_name}",
                        "summary": _truncate(top_claim.get("claim_text"), 100) or reason,
                        "body": (
                            f"{reason} Check for the next official update, downstream reporting, or a concrete second-order "
                            f"effect related to: {_truncate(top_claim.get('claim_text'), 180)}"
                        ),
                        "entity_ids": [entity_id],
                        "claim_ids": [top_claim["id"]] if top_claim.get("id") else [],
                        "metadata": {
                            "reason": reason,
                            "gap_kind": "follow_up",
                            "entity_id": entity_id,
                            "entity_name": entity_name,
                            "entity_type": entity.get("entity_type"),
                            "query": _entity_query_hint(entity, "follow_up"),
                            "trigger_claim_text": _truncate(top_claim.get("claim_text")),
                            "trigger_claim_importance": top_claim.get("importance"),
                            "trigger_claim_evidence_count": evidence_count_by_claim.get(top_claim["id"], 0),
                        },
                        "score": 70 + int((top_claim.get("importance") or 0) * 20),
                    }
                )

        if len(watch_sources) >= 3 or len(watch_claims) >= 3:
            reason = (
                f"{entity_name} is moving quickly across {len(watch_sources)} recent sources and {len(watch_claims)} recent claims."
            )
            suggestions.append(
                {
                    "type": "watch",
                    "title": f"Watch {entity_name}",
                    "summary": reason,
                    "body": (
                        f"{reason} Keep tracking it for additional evidence, competitor reactions, and any changes in the "
                        f"current narrative before the timeline goes stale."
                    ),
                    "entity_ids": [entity_id],
                    "claim_ids": [claim["id"] for claim in ranked_claims[:3] if claim.get("id")],
                    "metadata": {
                        "reason": reason,
                        "gap_kind": "watch",
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "entity_type": entity.get("entity_type"),
                        "query": _entity_query_hint(entity, "watch"),
                        "recent_source_count": len(watch_sources),
                        "recent_claim_count": len(watch_claims),
                        "tier_breakdown": tier_breakdown,
                    },
                    "score": 50 + len(watch_sources) * 6 + len(watch_claims) * 6,
                }
            )

    deduped: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for suggestion in sorted(
        suggestions,
        key=lambda item: (
            TYPE_PRIORITY.get(item["type"], 0),
            item.get("score", 0),
            item.get("title", ""),
        ),
        reverse=True,
    ):
        key = (suggestion["type"], suggestion["entity_ids"][0] if suggestion.get("entity_ids") else "")
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(suggestion)
        if len(deduped) >= MAX_SUGGESTIONS:
            break
    return deduped

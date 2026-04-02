"""Phase 2 source analysis extraction and readback helpers."""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import supabase

    from second_brain.providers.llm import LLMProvider

logger = logging.getLogger(__name__)

RUN_TYPE = "source_analysis"
PROMPT_VERSION = "phase2-claims-evidence-v1"
MAX_PROMPT_CHARS = 24000

ALLOWED_ENTITY_TYPES = {
    "company",
    "person",
    "product",
    "market",
    "technology",
    "country",
    "regulator",
    "investor",
    "publication",
    "other",
}
ALLOWED_ENTITY_ROLES = {
    "primary",
    "product",
    "competitor",
    "partner",
    "customer",
    "mentioned",
}
ALLOWED_CLAIM_TYPES = {
    "strategy",
    "product",
    "market",
    "financial",
    "organizational",
    "regulatory",
    "competitive",
    "causal",
    "prediction",
    "other",
}
ALLOWED_MODALITIES = {"reported", "asserted", "speculative", "historical"}
ALLOWED_STANCES = {"positive", "negative", "neutral"}
ALLOWED_LINK_TYPES = {"supports", "contradicts", "leads_to", "amplifies", "depends_on"}
ROLE_PRIORITY = {
    "primary": 5,
    "product": 4,
    "competitor": 3,
    "partner": 2,
    "customer": 2,
    "mentioned": 1,
}


def _now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _collapse_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _normalize_name(value: str | None) -> str | None:
    name = _collapse_whitespace(value)
    return name or None


def _normalize_enum(value: str | None, allowed: set[str], default: str) -> str:
    candidate = _collapse_whitespace(value).lower().replace("_", "-")
    return candidate if candidate in allowed else default


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, number)


def _coerce_timestamp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            parsed = dt.datetime.fromisoformat(text).replace(tzinfo=dt.UTC)
        else:
            parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.UTC)
        return parsed.isoformat()
    except ValueError:
        return None


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _parse_json_payload(text: str) -> dict[str, Any]:
    payload = _strip_json_fence(text)
    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Model response did not contain a JSON object")
    return json.loads(payload[start : end + 1])


def _build_prompt(
    source_row: dict[str, Any],
    chunk_rows: list[dict[str, Any]],
    lens_slugs: list[str],
) -> list[dict[str, str]]:
    source_text = _collapse_whitespace(source_row.get("raw_text"))
    if not source_text:
        source_text = "\n\n".join(_collapse_whitespace(chunk.get("content")) for chunk in chunk_rows)
    if not source_text:
        raise ValueError("Source has no text available for analysis")

    truncated = source_text[:MAX_PROMPT_CHARS]
    truncated_note = ""
    if len(source_text) > len(truncated):
        truncated_note = (
            "\nNote: the source text was truncated before extraction. Prefer the most central claims in the visible text."
        )

    metadata = {
        "title": source_row.get("title"),
        "author": source_row.get("author"),
        "url": source_row.get("url"),
        "published_at": source_row.get("published_at"),
        "kind": source_row.get("kind"),
        "tier": source_row.get("tier"),
        "publisher": source_row.get("publisher"),
        "language": source_row.get("language"),
    }

    return [
        {
            "role": "system",
            "content": (
                "You extract structured analytical primitives from a single source. "
                "Return JSON only. Do not add markdown, prose, or commentary."
            ),
        },
        {
            "role": "user",
            "content": (
                "Extract entities, claims, evidence, lenses, and claim-to-claim links from the source below.\n\n"
                "Rules:\n"
                f"- entity_type must be one of: {', '.join(sorted(ALLOWED_ENTITY_TYPES))}\n"
                f"- role must be one of: {', '.join(sorted(ALLOWED_ENTITY_ROLES))}\n"
                f"- claim_type must be one of: {', '.join(sorted(ALLOWED_CLAIM_TYPES))}\n"
                f"- modality must be one of: {', '.join(sorted(ALLOWED_MODALITIES))}\n"
                f"- stance must be one of: {', '.join(sorted(ALLOWED_STANCES))} or null\n"
                f"- lenses must use only these slugs: {', '.join(lens_slugs)}\n"
                f"- link_type must be one of: {', '.join(sorted(ALLOWED_LINK_TYPES))}\n"
                "- evidence quotes must be exact substrings from the source text\n"
                "- keep claims source-grounded, concrete, and non-duplicative\n"
                "- target_claim in links is a 1-based index into the claims array you return\n"
                "- prefer ISO 8601 timestamps when the source gives a concrete date, otherwise null\n\n"
                "Return this JSON shape exactly:\n"
                "{\n"
                '  "entities": [\n'
                "    {\n"
                '      "name": "Acme",\n'
                '      "entity_type": "company",\n'
                '      "ticker": null,\n'
                '      "aliases": ["Acme Corp"],\n'
                '      "role": "primary",\n'
                '      "mention_count": 3,\n'
                '      "salience": 0.9,\n'
                '      "metadata": {}\n'
                "    }\n"
                "  ],\n"
                '  "claims": [\n'
                "    {\n"
                '      "claim_text": "Acme launched Atlas for analysts.",\n'
                '      "claim_type": "product",\n'
                '      "modality": "reported",\n'
                '      "stance": "positive",\n'
                '      "subject_entity": "Acme",\n'
                '      "object_entity": "Atlas",\n'
                '      "normalized_claim": "acme launched atlas for analysts",\n'
                '      "event_at": null,\n'
                '      "event_end_at": null,\n'
                '      "confidence": 0.8,\n'
                '      "importance": 0.7,\n'
                '      "lenses": ["distribution"],\n'
                '      "evidence": [{"quote": "Acme launched Atlas for analysts.", "confidence": 0.9}],\n'
                '      "links": [{"target_claim": 2, "link_type": "leads_to", "confidence": 0.7, "explanation": "Launch sets up the later competitive effect."}],\n'
                '      "metadata": {}\n'
                "    }\n"
                "  ]\n"
                "}\n\n"
                f"Source metadata:\n{json.dumps(metadata, ensure_ascii=True)}{truncated_note}\n\n"
                f"Source text:\n{truncated}"
            ),
        },
    ]


def _normalize_entity_candidate(candidate: dict[str, Any]) -> dict[str, Any] | None:
    name = _normalize_name(candidate.get("name") or candidate.get("canonical_name"))
    if not name:
        return None
    aliases = [
        alias
        for alias in (
            _normalize_name(value)
            for value in candidate.get("aliases", []) or []
        )
        if alias and alias != name
    ]
    return {
        "name": name,
        "entity_type": _normalize_enum(candidate.get("entity_type"), ALLOWED_ENTITY_TYPES, "other"),
        "ticker": _normalize_name(candidate.get("ticker")),
        "aliases": _dedupe_preserve_order(aliases),
        "role": _normalize_enum(candidate.get("role"), ALLOWED_ENTITY_ROLES, "mentioned"),
        "mention_count": _coerce_int(candidate.get("mention_count")),
        "salience": _coerce_float(candidate.get("salience")),
        "metadata": candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {},
    }


def _normalize_claim_candidate(
    candidate: dict[str, Any],
    *,
    allowed_lenses: set[str],
) -> dict[str, Any] | None:
    claim_text = _collapse_whitespace(candidate.get("claim_text"))
    if not claim_text:
        return None
    evidence = []
    for raw_evidence in candidate.get("evidence", []) or []:
        if not isinstance(raw_evidence, dict):
            continue
        quote = _collapse_whitespace(raw_evidence.get("quote") or raw_evidence.get("evidence_text"))
        if not quote:
            continue
        evidence.append(
            {
                "quote": quote,
                "confidence": _coerce_float(raw_evidence.get("confidence")),
            }
        )
    if not evidence:
        evidence.append({"quote": claim_text, "confidence": _coerce_float(candidate.get("confidence"))})

    links = []
    for raw_link in candidate.get("links", []) or []:
        if not isinstance(raw_link, dict):
            continue
        try:
            target_claim = int(raw_link.get("target_claim"))
        except (TypeError, ValueError):
            continue
        links.append(
            {
                "target_claim": target_claim,
                "link_type": _normalize_enum(raw_link.get("link_type"), ALLOWED_LINK_TYPES, "supports"),
                "confidence": _coerce_float(raw_link.get("confidence")),
                "explanation": _collapse_whitespace(raw_link.get("explanation")) or None,
            }
        )

    stance_raw = candidate.get("stance")
    stance = None
    if stance_raw is not None and stance_raw != "":
        stance = _normalize_enum(stance_raw, ALLOWED_STANCES, "neutral")

    lenses = []
    for lens in candidate.get("lenses", []) or []:
        normalized = _collapse_whitespace(str(lens)).lower()
        if normalized in allowed_lenses:
            lenses.append(normalized)

    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    return {
        "claim_text": claim_text,
        "claim_type": _normalize_enum(candidate.get("claim_type"), ALLOWED_CLAIM_TYPES, "other"),
        "modality": _normalize_enum(candidate.get("modality"), ALLOWED_MODALITIES, "reported"),
        "stance": stance,
        "subject_entity": _normalize_name(candidate.get("subject_entity") or candidate.get("subject")),
        "object_entity": _normalize_name(candidate.get("object_entity") or candidate.get("object")),
        "normalized_claim": _collapse_whitespace(candidate.get("normalized_claim")) or claim_text.lower(),
        "event_at": _coerce_timestamp(candidate.get("event_at")),
        "event_end_at": _coerce_timestamp(candidate.get("event_end_at")),
        "confidence": _coerce_float(candidate.get("confidence")),
        "importance": _coerce_float(candidate.get("importance")),
        "lenses": _dedupe_preserve_order(lenses),
        "evidence": evidence,
        "links": links,
        "metadata": metadata,
    }


def _dedupe_claims(
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    seen: dict[tuple[str, str, str | None, str | None], int] = {}
    ordinal_map: dict[int, int] = {}

    for original_ordinal, claim in enumerate(claims, start=1):
        key = (
            claim["normalized_claim"].lower(),
            claim["claim_type"],
            claim.get("subject_entity"),
            claim.get("object_entity"),
        )
        existing = seen.get(key)
        if existing is not None:
            ordinal_map[original_ordinal] = existing
            continue
        kept.append(claim)
        new_ordinal = len(kept)
        seen[key] = new_ordinal
        ordinal_map[original_ordinal] = new_ordinal

    for ordinal, claim in enumerate(kept, start=1):
        unique_links: dict[tuple[int, str], dict[str, Any]] = {}
        for link in claim["links"]:
            target = ordinal_map.get(link["target_claim"])
            if target is None or target == ordinal:
                continue
            key = (target, link["link_type"])
            unique_links.setdefault(
                key,
                {
                    "target_claim": target,
                    "link_type": link["link_type"],
                    "confidence": link.get("confidence"),
                    "explanation": link.get("explanation"),
                },
            )
        claim["links"] = list(unique_links.values())

    return kept


def _merge_entity_candidates(
    entities: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    def add_entity(candidate: dict[str, Any]) -> None:
        key = (candidate["entity_type"], candidate["name"].lower())
        existing = merged.get(key)
        if existing is None:
            merged[key] = {
                **candidate,
                "aliases": list(candidate["aliases"]),
            }
            return
        if ROLE_PRIORITY[candidate["role"]] > ROLE_PRIORITY[existing["role"]]:
            existing["role"] = candidate["role"]
        existing["mention_count"] = max(
            existing.get("mention_count") or 0,
            candidate.get("mention_count") or 0,
        ) or None
        existing["salience"] = max(
            existing.get("salience") or 0.0,
            candidate.get("salience") or 0.0,
        ) or None
        if not existing.get("ticker") and candidate.get("ticker"):
            existing["ticker"] = candidate["ticker"]
        existing["aliases"] = _dedupe_preserve_order(existing["aliases"] + candidate["aliases"])
        existing["metadata"] = {**existing["metadata"], **candidate["metadata"]}

    for entity in entities:
        add_entity(entity)

    known_names = {entity["name"].lower(): entity["entity_type"] for entity in merged.values()}
    for claim in claims:
        for field_name in ("subject_entity", "object_entity"):
            entity_name = claim.get(field_name)
            if not entity_name:
                continue
            entity_type = known_names.get(entity_name.lower(), "other")
            add_entity(
                {
                    "name": entity_name,
                    "entity_type": entity_type,
                    "ticker": None,
                    "aliases": [],
                    "role": "mentioned",
                    "mention_count": None,
                    "salience": None,
                    "metadata": {},
                }
            )

    return list(merged.values())


def _extract_candidates(
    source_row: dict[str, Any],
    chunk_rows: list[dict[str, Any]],
    llm_provider: "LLMProvider",
    lens_slugs: list[str],
) -> dict[str, Any]:
    response = llm_provider.complete(_build_prompt(source_row, chunk_rows, lens_slugs), temperature=0)
    payload = _parse_json_payload(response)

    raw_entities = payload.get("entities", []) if isinstance(payload, dict) else []
    raw_claims = payload.get("claims", []) if isinstance(payload, dict) else []

    entities = [
        normalized
        for normalized in (
            _normalize_entity_candidate(candidate)
            for candidate in raw_entities if isinstance(candidate, dict)
        )
        if normalized is not None
    ]
    claims = [
        normalized
        for normalized in (
            _normalize_claim_candidate(candidate, allowed_lenses=set(lens_slugs))
            for candidate in raw_claims if isinstance(candidate, dict)
        )
        if normalized is not None
    ]
    claims = _dedupe_claims(claims)
    entities = _merge_entity_candidates(entities, claims)

    return {
        "entities": entities,
        "claims": claims,
        "raw_response": response,
    }


def _find_text_position(haystack: str, needle: str) -> int:
    if not haystack or not needle:
        return -1
    position = haystack.find(needle)
    if position != -1:
        return position
    return haystack.lower().find(needle.lower())


def _locate_evidence(
    evidence_text: str,
    source_text: str,
    chunk_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    quote = evidence_text.strip()
    for chunk in chunk_rows:
        content = chunk.get("content") or ""
        position = _find_text_position(content, quote)
        if position != -1:
            return {
                "chunk_id": chunk.get("id"),
                "start_char": position,
                "end_char": position + len(quote),
            }

    position = _find_text_position(source_text, quote)
    if position != -1:
        return {
            "chunk_id": None,
            "start_char": position,
            "end_char": position + len(quote),
        }
    return {"chunk_id": None, "start_char": None, "end_char": None}


def _start_processing_run(
    db: "supabase.Client",
    *,
    source_id: str,
    model: str | None,
) -> str:
    payload = {
        "run_type": RUN_TYPE,
        "status": "running",
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "started_at": _now_iso(),
        "metadata": {"source_id": source_id},
    }
    result = db.table("processing_runs").insert(payload).execute()
    if result.data:
        return result.data[0]["id"]
    raise RuntimeError("Failed to create processing run")


def _finish_processing_run(
    db: "supabase.Client",
    *,
    run_id: str,
    source_id: str,
    status: str,
    metadata: dict[str, Any],
) -> None:
    db.table("processing_runs").update(
        {
            "status": status,
            "finished_at": _now_iso(),
            "metadata": {"source_id": source_id, **metadata},
        }
    ).eq("id", run_id).execute()


def _load_source_row(db: "supabase.Client", source_id: str) -> dict[str, Any]:
    rows = (
        db.table("sources")
        .select(
            "id, title, author, url, published_at, source_type, readwise_id, external_id, "
            "kind, tier, publisher, remote_updated_at, parent_source_id, thread_key, "
            "language, metadata, ingested_at, updated_at, raw_text"
        )
        .eq("id", source_id)
        .execute()
        .data
        or []
    )
    if not rows:
        raise ValueError(f"Source {source_id} not found")
    return rows[0]


def _load_chunks(db: "supabase.Client", source_id: str) -> list[dict[str, Any]]:
    return (
        db.table("chunks")
        .select("id, source_id, chunk_index, content, start_char, end_char")
        .eq("source_id", source_id)
        .order("chunk_index")
        .execute()
        .data
        or []
    )


def _load_lenses(db: "supabase.Client") -> list[dict[str, Any]]:
    return db.table("lenses").select("id, slug, name, description").execute().data or []


def _clear_existing_analysis(db: "supabase.Client", source_id: str) -> None:
    existing_claims = db.table("claims").select("id").eq("source_id", source_id).execute().data or []
    claim_ids = [row["id"] for row in existing_claims]
    if claim_ids:
        db.table("claim_links").delete().in_("from_claim_id", claim_ids).execute()
        db.table("claim_links").delete().in_("to_claim_id", claim_ids).execute()
        db.table("claim_evidence").delete().in_("claim_id", claim_ids).execute()
        db.table("claim_lenses").delete().in_("claim_id", claim_ids).execute()
    db.table("claims").delete().eq("source_id", source_id).execute()
    db.table("source_entities").delete().eq("source_id", source_id).execute()


def _ensure_entity(db: "supabase.Client", candidate: dict[str, Any]) -> str:
    rows = (
        db.table("entities")
        .select("id, ticker, metadata")
        .eq("entity_type", candidate["entity_type"])
        .eq("canonical_name", candidate["name"])
        .execute()
        .data
        or []
    )
    if rows:
        entity_id = rows[0]["id"]
        merged_metadata = {
            **(rows[0].get("metadata") or {}),
            **candidate["metadata"],
        }
        update_payload: dict[str, Any] = {"updated_at": _now_iso(), "metadata": merged_metadata}
        if candidate.get("ticker"):
            update_payload["ticker"] = candidate["ticker"]
        db.table("entities").update(update_payload).eq("id", entity_id).execute()
        return entity_id

    result = db.table("entities").insert(
        {
            "canonical_name": candidate["name"],
            "entity_type": candidate["entity_type"],
            "ticker": candidate.get("ticker"),
            "metadata": candidate["metadata"],
        }
    ).execute()
    if not result.data:
        raise RuntimeError(f"Failed to create entity {candidate['name']}")
    return result.data[0]["id"]


def _ensure_alias(db: "supabase.Client", entity_id: str, alias: str) -> None:
    existing = (
        db.table("entity_aliases")
        .select("id")
        .eq("entity_id", entity_id)
        .eq("alias", alias)
        .execute()
        .data
        or []
    )
    if existing:
        return
    db.table("entity_aliases").insert(
        {
            "entity_id": entity_id,
            "alias": alias,
            "alias_type": "name",
        }
    ).execute()


def _persist_analysis(
    db: "supabase.Client",
    *,
    source_row: dict[str, Any],
    chunk_rows: list[dict[str, Any]],
    run_id: str,
    candidates: dict[str, Any],
    lenses: list[dict[str, Any]],
) -> dict[str, int]:
    source_id = source_row["id"]
    source_text = source_row.get("raw_text") or "\n\n".join(chunk.get("content") or "" for chunk in chunk_rows)
    lens_id_by_slug = {lens["slug"]: lens["id"] for lens in lenses}

    _clear_existing_analysis(db, source_id)

    entity_ids_by_name: dict[str, str] = {}
    for entity in candidates["entities"]:
        entity_id = _ensure_entity(db, entity)
        entity_ids_by_name[entity["name"].lower()] = entity_id
        for alias in entity["aliases"]:
            _ensure_alias(db, entity_id, alias)
        db.table("source_entities").insert(
            {
                "source_id": source_id,
                "entity_id": entity_id,
                "role": entity["role"],
                "mention_count": entity.get("mention_count"),
                "salience": entity.get("salience"),
            }
        ).execute()

    claim_ids_by_ordinal: dict[int, str] = {}
    evidence_count = 0
    claim_lens_count = 0

    for ordinal, claim in enumerate(candidates["claims"], start=1):
        result = db.table("claims").insert(
            {
                "source_id": source_id,
                "subject_entity_id": entity_ids_by_name.get((claim.get("subject_entity") or "").lower()),
                "object_entity_id": entity_ids_by_name.get((claim.get("object_entity") or "").lower()),
                "claim_type": claim["claim_type"],
                "modality": claim["modality"],
                "stance": claim["stance"],
                "claim_text": claim["claim_text"],
                "normalized_claim": claim["normalized_claim"],
                "event_at": claim["event_at"],
                "event_end_at": claim["event_end_at"],
                "confidence": claim["confidence"],
                "importance": claim["importance"],
                "extraction_run_id": run_id,
                "metadata": {"ordinal": ordinal, **claim["metadata"]},
            }
        ).execute()
        if not result.data:
            raise RuntimeError(f"Failed to create claim {ordinal}")
        claim_id = result.data[0]["id"]
        claim_ids_by_ordinal[ordinal] = claim_id

        for evidence in claim["evidence"]:
            located = _locate_evidence(evidence["quote"], source_text, chunk_rows)
            db.table("claim_evidence").insert(
                {
                    "claim_id": claim_id,
                    "source_id": source_id,
                    "chunk_id": located["chunk_id"],
                    "evidence_text": evidence["quote"],
                    "start_char": located["start_char"],
                    "end_char": located["end_char"],
                    "confidence": evidence.get("confidence"),
                }
            ).execute()
            evidence_count += 1

        for lens_slug in claim["lenses"]:
            lens_id = lens_id_by_slug.get(lens_slug)
            if not lens_id:
                continue
            db.table("claim_lenses").insert(
                {
                    "claim_id": claim_id,
                    "lens_id": lens_id,
                    "weight": claim.get("importance"),
                }
            ).execute()
            claim_lens_count += 1

    link_count = 0
    inserted_links: set[tuple[str, str, str]] = set()
    for ordinal, claim in enumerate(candidates["claims"], start=1):
        from_claim_id = claim_ids_by_ordinal[ordinal]
        for link in claim["links"]:
            to_claim_id = claim_ids_by_ordinal.get(link["target_claim"])
            if not to_claim_id:
                continue
            dedupe_key = (from_claim_id, to_claim_id, link["link_type"])
            if dedupe_key in inserted_links:
                continue
            db.table("claim_links").insert(
                {
                    "from_claim_id": from_claim_id,
                    "to_claim_id": to_claim_id,
                    "link_type": link["link_type"],
                    "confidence": link.get("confidence"),
                    "explanation": link.get("explanation"),
                }
            ).execute()
            inserted_links.add(dedupe_key)
            link_count += 1

    return {
        "entity_count": len(candidates["entities"]),
        "claim_count": len(candidates["claims"]),
        "evidence_count": evidence_count,
        "claim_lens_count": claim_lens_count,
        "link_count": link_count,
    }


def _latest_run_for_source(db: "supabase.Client", source_id: str) -> dict[str, Any] | None:
    rows = (
        db.table("processing_runs")
        .select("id, status, model, prompt_version, started_at, finished_at, metadata")
        .eq("run_type", RUN_TYPE)
        .order("started_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    for row in rows:
        metadata = row.get("metadata") or {}
        if metadata.get("source_id") == source_id:
            return row
    return None


def get_source_analysis(source_id: str, db: "supabase.Client") -> dict[str, Any]:
    source_entities = (
        db.table("source_entities")
        .select("source_id, entity_id, role, mention_count, salience")
        .eq("source_id", source_id)
        .execute()
        .data
        or []
    )
    entity_ids = [row["entity_id"] for row in source_entities]
    entities = []
    entity_lookup: dict[str, dict[str, Any]] = {}

    if entity_ids:
        entity_rows = db.table("entities").select(
            "id, canonical_name, entity_type, ticker, metadata"
        ).in_("id", entity_ids).execute().data or []
        alias_rows = db.table("entity_aliases").select(
            "entity_id, alias, alias_type, confidence"
        ).in_("entity_id", entity_ids).execute().data or []
        aliases_by_entity: dict[str, list[dict[str, Any]]] = {}
        for alias in alias_rows:
            aliases_by_entity.setdefault(alias["entity_id"], []).append(alias)
        entity_rows_by_id = {row["id"]: row for row in entity_rows}
        for source_entity in source_entities:
            entity_row = entity_rows_by_id.get(source_entity["entity_id"])
            if not entity_row:
                continue
            payload = {
                "id": entity_row["id"],
                "canonical_name": entity_row["canonical_name"],
                "entity_type": entity_row["entity_type"],
                "ticker": entity_row.get("ticker"),
                "metadata": entity_row.get("metadata") or {},
                "role": source_entity.get("role"),
                "mention_count": source_entity.get("mention_count"),
                "salience": source_entity.get("salience"),
                "aliases": aliases_by_entity.get(entity_row["id"], []),
            }
            entities.append(payload)
            entity_lookup[entity_row["id"]] = payload

    claims = (
        db.table("claims")
        .select(
            "id, source_id, subject_entity_id, object_entity_id, claim_type, modality, stance, "
            "claim_text, normalized_claim, event_at, event_end_at, confidence, importance, "
            "extraction_run_id, metadata, created_at"
        )
        .eq("source_id", source_id)
        .order("importance", desc=True)
        .execute()
        .data
        or []
    )
    claim_ids = [row["id"] for row in claims]

    evidence_rows = []
    claim_lens_rows = []
    link_rows = []
    if claim_ids:
        evidence_rows = db.table("claim_evidence").select(
            "id, claim_id, source_id, chunk_id, evidence_text, start_char, end_char, confidence, created_at"
        ).in_("claim_id", claim_ids).execute().data or []
        claim_lens_rows = db.table("claim_lenses").select(
            "claim_id, lens_id, weight"
        ).in_("claim_id", claim_ids).execute().data or []
        link_rows = db.table("claim_links").select(
            "id, from_claim_id, to_claim_id, link_type, confidence, explanation, created_at"
        ).in_("from_claim_id", claim_ids).execute().data or []

    chunk_ids = [row["chunk_id"] for row in evidence_rows if row.get("chunk_id")]
    chunk_lookup: dict[str, dict[str, Any]] = {}
    if chunk_ids:
        chunk_rows = db.table("chunks").select(
            "id, chunk_index, content"
        ).in_("id", chunk_ids).execute().data or []
        chunk_lookup = {row["id"]: row for row in chunk_rows}

    lenses = db.table("lenses").select("id, slug, name, description").execute().data or []
    lens_lookup = {lens["id"]: lens for lens in lenses}

    evidence_by_claim: dict[str, list[dict[str, Any]]] = {}
    for evidence in evidence_rows:
        chunk = chunk_lookup.get(evidence.get("chunk_id"))
        evidence_by_claim.setdefault(evidence["claim_id"], []).append(
            {
                **evidence,
                "chunk_index": chunk.get("chunk_index") if chunk else None,
            }
        )

    lenses_by_claim: dict[str, list[dict[str, Any]]] = {}
    for claim_lens in claim_lens_rows:
        lens = lens_lookup.get(claim_lens["lens_id"])
        if not lens:
            continue
        lenses_by_claim.setdefault(claim_lens["claim_id"], []).append(
            {
                "id": lens["id"],
                "slug": lens["slug"],
                "name": lens["name"],
                "description": lens.get("description"),
                "weight": claim_lens.get("weight"),
            }
        )

    links_by_claim: dict[str, list[dict[str, Any]]] = {}
    claim_lookup = {claim["id"]: claim for claim in claims}
    for link in link_rows:
        target_claim = claim_lookup.get(link["to_claim_id"])
        links_by_claim.setdefault(link["from_claim_id"], []).append(
            {
                **link,
                "target_claim_text": target_claim.get("claim_text") if target_claim else None,
            }
        )

    claim_payloads = [
        {
            **claim,
            "subject_entity": entity_lookup.get(claim.get("subject_entity_id")),
            "object_entity": entity_lookup.get(claim.get("object_entity_id")),
            "evidence": evidence_by_claim.get(claim["id"], []),
            "lenses": lenses_by_claim.get(claim["id"], []),
            "links": links_by_claim.get(claim["id"], []),
        }
        for claim in claims
    ]

    entities.sort(key=lambda entity: entity.get("salience") or 0, reverse=True)
    return {
        "entities": entities,
        "claims": claim_payloads,
        "latest_run": _latest_run_for_source(db, source_id),
    }


def analyze_source(
    source_id: str,
    db: "supabase.Client",
    llm_provider: "LLMProvider",
) -> dict[str, Any]:
    model = getattr(llm_provider, "_model", None)
    run_id = _start_processing_run(db, source_id=source_id, model=model)

    try:
        source_row = _load_source_row(db, source_id)
        chunk_rows = _load_chunks(db, source_id)
        lenses = _load_lenses(db)
        lens_slugs = [lens["slug"] for lens in lenses]
        candidates = _extract_candidates(source_row, chunk_rows, llm_provider, lens_slugs)
        counts = _persist_analysis(
            db,
            source_row=source_row,
            chunk_rows=chunk_rows,
            run_id=run_id,
            candidates=candidates,
            lenses=lenses,
        )
        _finish_processing_run(
            db,
            run_id=run_id,
            source_id=source_id,
            status="completed",
            metadata=counts,
        )
    except Exception as exc:
        logger.exception("Source analysis failed for %s", source_id)
        _finish_processing_run(
            db,
            run_id=run_id,
            source_id=source_id,
            status="failed",
            metadata={"error": str(exc)},
        )
        raise

    return {
        "status": "completed",
        "run_id": run_id,
        **counts,
        "analysis": get_source_analysis(source_id, db),
    }

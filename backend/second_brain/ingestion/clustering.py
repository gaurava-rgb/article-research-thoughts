"""
Topic clustering and assignment helpers for Phase 3.

This module provides the smallest durable topic-structure backend slice:

1. read stored whole-source embeddings from `sources.source_embedding`
2. match a source embedding against stored topic centroids via SQL
3. assign a source to an existing or newly created topic
4. recompute topic centroids after memberships change
5. fetch topic sources with date filtering that falls back to `ingested_at`

It intentionally stops short of sync orchestration, topic summaries, and UI work.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from second_brain.providers.llm import LLMProvider

SIMILARITY_THRESHOLD = 0.65
_TOPIC_NAME_MAX_LENGTH = 80
_TOPIC_NAMING_PREVIEW_CHARS = 600


def _parse_embedding(raw) -> list[float] | None:
    """Normalize a Supabase vector value to list[float].

    Supabase/PostgREST returns vector columns as a JSON string like
    '[0.1,0.2,...]' instead of a Python list. Parse it when needed.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        import json
        return json.loads(raw)
    return raw


@dataclass(frozen=True)
class TopicAssignmentResult:
    source_id: str
    topic_id: str | None
    created_topic: bool
    similarity: float
    reason: str


@dataclass(frozen=True)
class TopicAssignmentBatchResult:
    processed_count: int
    assigned_existing_count: int
    created_topic_count: int
    skipped_missing_embedding_count: int


def get_source_embedding(source_id: str, db) -> list[float] | None:
    """Return the stored whole-source embedding for a source, if present."""
    rows = (
        db.table("sources")
        .select("source_embedding")
        .eq("id", source_id)
        .execute()
    ).data
    if not rows:
        return None
    return rows[0].get("source_embedding")


def get_source_record(source_id: str, db) -> dict | None:
    """Return the stored source row needed for topic assignment."""
    rows = (
        db.table("sources")
        .select("id, title, raw_text, source_embedding")
        .eq("id", source_id)
        .execute()
    ).data
    if not rows:
        return None
    return rows[0]


def find_best_topic(
    source_embedding: list[float],
    db,
    match_threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[str | None, float]:
    """Return the best topic id and similarity from the `match_topic` SQL helper."""
    response = db.rpc(
        "match_topic",
        {
            "query_embedding": source_embedding,
            "match_threshold": match_threshold,
            "match_count": 1,
        },
    ).execute()
    error = getattr(response, "error", None)
    if error:
        raise RuntimeError(f"Topic match failed: {error}")
    if not response.data:
        return None, 0.0

    best = response.data[0]
    return best["topic_id"], float(best["similarity"])


def _clean_topic_name(raw_name: str, fallback_title: str) -> str:
    cleaned = " ".join((raw_name or "").strip().split())
    cleaned = cleaned.strip("\"'` ").rstrip(" .,:;!?-")
    if cleaned:
        return cleaned[:_TOPIC_NAME_MAX_LENGTH]

    fallback = " ".join((fallback_title or "").strip().split())
    if fallback:
        return fallback[:_TOPIC_NAME_MAX_LENGTH]
    return "Untitled Topic"


def generate_topic_name(source: dict, llm_provider: "LLMProvider") -> str:
    """Use the LLM only when a source needs to seed a brand-new topic."""
    title = (source.get("title") or "Untitled article").strip()
    preview = (source.get("raw_text") or "").strip()[:_TOPIC_NAMING_PREVIEW_CHARS]
    response = llm_provider.complete(
        [
            {
                "role": "system",
                "content": (
                    "You name topics for a personal knowledge base. "
                    "Return only a short 2-6 word topic name, with no quotes or explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Article title: {title}\n\n"
                    f"Article preview:\n{preview}\n\n"
                    "Return the single best topic name."
                ),
            },
        ],
        temperature=0.2,
    )
    return _clean_topic_name(response.splitlines()[0] if response else "", title)


def create_topic(source: dict, llm_provider: "LLMProvider", db) -> tuple[str, str]:
    """Create a new topic seeded by one source."""
    topic_id = str(uuid4())
    topic_name = generate_topic_name(source, llm_provider)
    (
        db.table("topics")
        .insert(
            {
                "id": topic_id,
                "name": topic_name,
                "centroid_embedding": _parse_embedding(source["source_embedding"]),
            }
        )
        .execute()
    )
    return topic_id, topic_name


def assign_source_to_topic(source_id: str, topic_id: str, db) -> bool:
    """Insert one durable source-topic membership, skipping duplicates."""
    existing = (
        db.table("source_topics")
        .select("source_id")
        .eq("source_id", source_id)
        .eq("topic_id", topic_id)
        .execute()
    ).data
    if existing:
        return False

    db.table("source_topics").insert({"source_id": source_id, "topic_id": topic_id}).execute()
    update_topic_centroid(topic_id, db)
    return True


def assign_topic_to_source(
    source_id: str,
    db,
    llm_provider: "LLMProvider",
    match_threshold: float = SIMILARITY_THRESHOLD,
) -> TopicAssignmentResult:
    """Assign one source to the best existing topic or create a new one."""
    source = get_source_record(source_id, db)
    if not source:
        return TopicAssignmentResult(
            source_id=source_id,
            topic_id=None,
            created_topic=False,
            similarity=0.0,
            reason="missing_source",
        )

    source_embedding = _parse_embedding(source.get("source_embedding"))
    if not source_embedding:
        return TopicAssignmentResult(
            source_id=source_id,
            topic_id=None,
            created_topic=False,
            similarity=0.0,
            reason="missing_source_embedding",
        )

    topic_id, similarity = find_best_topic(
        source_embedding,
        db,
        match_threshold=match_threshold,
    )
    if topic_id is not None:
        assign_source_to_topic(source_id, topic_id, db)
        return TopicAssignmentResult(
            source_id=source_id,
            topic_id=topic_id,
            created_topic=False,
            similarity=similarity,
            reason="assigned_existing_topic",
        )

    topic_id, _topic_name = create_topic(source, llm_provider, db)
    assign_source_to_topic(source_id, topic_id, db)
    return TopicAssignmentResult(
        source_id=source_id,
        topic_id=topic_id,
        created_topic=True,
        similarity=0.0,
        reason="created_topic",
    )


def assign_topics_to_unassigned_sources(
    db,
    llm_provider: "LLMProvider",
    limit: int | None = None,
    match_threshold: float = SIMILARITY_THRESHOLD,
) -> TopicAssignmentBatchResult:
    """Assign topics to sources that do not yet have any membership rows."""
    source_rows = db.table("sources").select("id").execute().data
    assignment_rows = db.table("source_topics").select("source_id").execute().data
    assigned_source_ids = {row["source_id"] for row in assignment_rows}
    unassigned_source_ids = [
        row["id"] for row in source_rows if row["id"] not in assigned_source_ids
    ]
    if limit is not None:
        unassigned_source_ids = unassigned_source_ids[:limit]

    assigned_existing_count = 0
    created_topic_count = 0
    skipped_missing_embedding_count = 0

    for source_id in unassigned_source_ids:
        result = assign_topic_to_source(
            source_id,
            db,
            llm_provider,
            match_threshold=match_threshold,
        )
        if result.reason == "assigned_existing_topic":
            assigned_existing_count += 1
        elif result.reason == "created_topic":
            created_topic_count += 1
        elif result.reason == "missing_source_embedding":
            skipped_missing_embedding_count += 1

    return TopicAssignmentBatchResult(
        processed_count=len(unassigned_source_ids),
        assigned_existing_count=assigned_existing_count,
        created_topic_count=created_topic_count,
        skipped_missing_embedding_count=skipped_missing_embedding_count,
    )


def update_topic_centroid(topic_id: str, db) -> list[float] | None:
    """
    Recompute and persist a normalized centroid for a topic.

    Returning the centroid makes this helper easy to test and lets later Phase 3
    code reuse the freshly computed vector without re-querying.
    """
    rows = (
        db.table("source_topics")
        .select("sources(source_embedding)")
        .eq("topic_id", topic_id)
        .execute()
    ).data

    vectors = [
        _parse_embedding(source["source_embedding"])
        for row in rows
        if (source := row.get("sources")) and source.get("source_embedding")
    ]
    if not vectors:
        return None

    dimensions = len(vectors[0])
    centroid = [
        sum(vector[index] for vector in vectors) / len(vectors)
        for index in range(dimensions)
    ]
    magnitude = sqrt(sum(value * value for value in centroid))
    if magnitude == 0:
        return None

    normalized = [value / magnitude for value in centroid]
    (
        db.table("topics")
        .update({"centroid_embedding": normalized})
        .eq("id", topic_id)
        .execute()
    )
    return normalized


def get_topic_sources_by_date(
    topic_id: str,
    after: str | None,
    before: str | None,
    db,
) -> list[dict]:
    """
    Return sources in a topic filtered by effective date.

    `published_at` is preferred, but `ingested_at` keeps sources with missing
    publication metadata usable in later temporal topic analysis.
    """
    rows = (
        db.table("source_topics")
        .select("sources(id, title, author, url, published_at, ingested_at)")
        .eq("topic_id", topic_id)
        .execute()
    ).data
    sources = [row["sources"] for row in rows if row.get("sources")]

    def in_range(source: dict) -> bool:
        effective_date = (source.get("published_at") or source.get("ingested_at") or "")[:10]
        if not effective_date:
            return False
        if after and effective_date < after:
            return False
        if before and effective_date > before:
            return False
        return True

    return [source for source in sources if in_range(source)]


__all__ = [
    "SIMILARITY_THRESHOLD",
    "TopicAssignmentBatchResult",
    "TopicAssignmentResult",
    "assign_source_to_topic",
    "assign_topic_to_source",
    "assign_topics_to_unassigned_sources",
    "create_topic",
    "find_best_topic",
    "get_source_embedding",
    "get_source_record",
    "get_topic_sources_by_date",
    "generate_topic_name",
    "update_topic_centroid",
]

"""insights.py — Proactive insights generation (Phase 5: WORK-01, WORK-02, WORK-03).

Generates weekly digests summarizing recent articles by topic, and stores
them in the `insights` table for the user to read at their leisure.

The `insights` table schema (from schema.sql):
  id         UUID  PK
  type       TEXT  — 'pattern' | 'contradiction' | 'digest'
  title      TEXT
  body       TEXT
  seen       BOOL  DEFAULT false
  created_at TIMESTAMPTZ
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def generate_digest(db, llm_provider) -> dict | None:
    """Generate a weekly digest from sources ingested in the last 7 days.

    Steps:
      1. Query sources ingested since 7 days ago.
      2. Join with source_topics to get each article's topic assignment.
      3. Group articles by topic and build a structured context block.
      4. Ask the LLM to synthesize what themes emerged this week.
      5. Save the result as a 'digest' insight row.

    Args:
        db: Supabase client.
        llm_provider: An LLMProvider instance (from providers/llm.py).

    Returns:
        The saved insight dict (id, type, title, body, seen, created_at),
        or None if no articles were ingested in the last 7 days.
    """
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

    # Fetch topic assignments for these sources
    source_ids = [s["id"] for s in sources]
    memberships = (
        db.table("source_topics")
        .select("source_id, topics(id, name)")
        .in_("source_id", source_ids)
        .execute()
        .data
    ) or []

    # Build source_id → topic name lookup
    source_to_topic: dict[str, str] = {}
    for m in memberships:
        t = m.get("topics")
        if t:
            source_to_topic[m["source_id"]] = t["name"]

    # Group articles by topic
    topic_articles: dict[str, list[str]] = {}
    for s in sources:
        topic_name = source_to_topic.get(s["id"], "Uncategorized")
        topic_articles.setdefault(topic_name, []).append(s["title"])

    # Build LLM context (top 10 topics, up to 8 titles each)
    lines = [f"Articles saved in the last 7 days ({len(sources)} total):\n"]
    for topic_name, titles in sorted(topic_articles.items(), key=lambda x: -len(x[1]))[:10]:
        lines.append(f"**{topic_name}** ({len(titles)} article{'s' if len(titles) != 1 else ''}):")
        for t in titles[:8]:
            lines.append(f"  - {t}")
        lines.append("")

    context = "\n".join(lines)

    summary = llm_provider.complete([
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
    ])

    title = f"Weekly Digest — {datetime.now().strftime('%B %d, %Y')}"
    row = (
        db.table("insights")
        .insert({"type": "digest", "title": title, "body": summary, "seen": False})
        .execute()
        .data[0]
    )
    return row


def get_insights(db) -> dict:
    """Return all insights ordered newest-first, plus the unseen count.

    Returns:
        {
          "insights": [{id, type, title, body, seen, created_at}, ...],
          "unseen_count": int
        }
    """
    rows = (
        db.table("insights")
        .select("id, type, title, body, seen, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
    ) or []

    unseen_count = sum(1 for r in rows if not r.get("seen", True))
    return {"insights": rows, "unseen_count": unseen_count}


def mark_seen(db, insight_id: str) -> None:
    """Mark a single insight as seen."""
    db.table("insights").update({"seen": True}).eq("id", insight_id).execute()

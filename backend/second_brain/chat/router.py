"""FastAPI router for chat, conversation management, and sync endpoints.

Endpoints:
  POST   /api/chat                      — return one complete chat response as JSON
  POST   /api/conversations             — create new conversation
  GET    /api/conversations             — list conversations (sidebar)
  GET    /api/conversations/{id}/messages — load conversation history
  PATCH  /api/conversations/{id}        — update title

/api/chat response shape:
  {"content": "<full assistant reply>", "sources": [...]}
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a personal knowledge assistant. The user is asking questions about "
    "articles, essays, and ideas they have saved to their Second Brain. "
    "Always structure your response with these exact section headers — even when "
    "sources are not directly relevant:\n\n"
    "[FROM YOUR SOURCES]\n"
    "Narrative synthesis of what their saved articles say. Write flowing prose, not "
    "bullet points. Cite article titles in bold: **Title**. If nothing is relevant, "
    "say so honestly inside this section.\n\n"
    "[ANALYSIS]\n"
    "Your synthesis: patterns, tensions, and what their reading reveals.\n\n"
    "Only add [CONTRADICTIONS] when sources genuinely disagree: "
    "'**Source A** argues X, while **Source B** argues Y.' "
    "Never fabricate sources. Always output both [FROM YOUR SOURCES] and [ANALYSIS]."
)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationPatch(BaseModel):
    title: str


def _load_source_rows(source_ids: list[str]) -> dict[str, dict]:
    if not source_ids:
        return {}

    from second_brain.db import get_db_client

    rows = (
        get_db_client()
        .table("sources")
        .select(
            "id, title, author, url, published_at, source_type, readwise_id, external_id, "
            "kind, tier, publisher, remote_updated_at, parent_source_id, thread_key, language, metadata"
        )
        .in_("id", source_ids)
        .execute()
        .data
        or []
    )
    return {row["id"]: row for row in rows}


def _serialize_source_payload(search_result, source_row: dict | None) -> dict:
    return {
        "source_id": search_result.source_id,
        "title": search_result.title,
        "url": search_result.url,
        "author": search_result.author,
        "score": round(search_result.hybrid_score, 3),
        "published_at": search_result.published_at,
        "kind": search_result.kind or (source_row or {}).get("kind"),
        "tier": search_result.tier or (source_row or {}).get("tier"),
        "publisher": search_result.publisher or (source_row or {}).get("publisher"),
    }


@router.post("/chat")
async def chat_endpoint(body: ChatRequest) -> dict:
    """Return one complete assistant reply and cited sources as JSON."""
    from second_brain.retrieval.search import hybrid_search, SearchResult
    from second_brain.chat.conversation import (
        get_messages,
        save_message,
        build_messages_for_llm,
    )
    from second_brain.config import cfg
    from openai import AsyncOpenAI

    # 1. Retrieve relevant source chunks, deduplicated by source article
    raw_results: list[SearchResult] = hybrid_search(body.message, top_k=30)
    seen: set[str] = set()
    sources: list[SearchResult] = []
    for r in raw_results:
        if r.source_id not in seen:
            seen.add(r.source_id)
            sources.append(r)

    source_rows = _load_source_rows([source.source_id for source in sources])

    sources_for_prompt = "\n\n".join(
        f"[Source: {s.title}]\n{s.content}" for s in sources
    )
    sources_json = [
        _serialize_source_payload(s, source_rows.get(s.source_id))
        for s in sources
    ]

    # 2. Build LLM messages with history (CHAT-01)
    history = get_messages(body.conversation_id)
    history_for_llm = [{"role": m["role"], "content": m["content"]} for m in history]

    full_system = SYSTEM_PROMPT
    if sources_for_prompt:
        full_system += f"\n\nRelevant sources from the user's knowledge base:\n{sources_for_prompt}"

    messages = build_messages_for_llm(
        system_prompt=full_system,
        history=history_for_llm,
        user_message=body.message,
    )

    # 3. Save user message
    save_message(body.conversation_id, "user", body.message)

    # 4. Call LLM and collect full response
    client = AsyncOpenAI(
        base_url=cfg.llm.base_url,
        api_key=cfg.llm.api_key,
    )
    completion = await client.chat.completions.create(
        model=cfg.llm.model,
        messages=messages,
    )
    complete_response = completion.choices[0].message.content or ""

    # 5. Save assistant message (no embedding — source articles are the retrieval
    #    ground truth; embedding AI responses would feed derivatives back into future
    #    prompts and cause the model to cite itself instead of your reading)
    if complete_response:
        save_message(body.conversation_id, "assistant", complete_response)

    return {"content": complete_response, "sources": sources_json}


@router.post("/conversations")
def create_conversation_endpoint(body: ConversationCreate = ConversationCreate()):
    """Create a new conversation and return it."""
    from second_brain.chat.conversation import create_conversation
    return create_conversation(title=body.title)


@router.get("/conversations")
def list_conversations_endpoint():
    """Return all conversations ordered by most recently updated (for sidebar)."""
    from second_brain.chat.conversation import list_conversations
    return list_conversations(limit=50)


@router.get("/conversations/{conversation_id}/messages")
def get_messages_endpoint(conversation_id: str):
    """Return all messages for a conversation in chronological order."""
    from second_brain.chat.conversation import get_messages
    return get_messages(conversation_id)


@router.get("/sources/{source_id}")
def get_source_detail_endpoint(source_id: str):
    """Return source metadata plus any stored Phase 2 analysis."""
    from second_brain.db import get_db_client
    from second_brain.analysis.extraction import get_source_analysis

    db = get_db_client()
    rows = (
        db
        .table("sources")
        .select(
            "id, title, author, url, published_at, ingested_at, updated_at, source_type, "
            "readwise_id, external_id, kind, tier, publisher, remote_updated_at, "
            "parent_source_id, thread_key, language, metadata"
        )
        .eq("id", source_id)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source not found")
    source = rows[0]
    analysis = get_source_analysis(source_id, db)
    return {
        **source,
        "analysis": {
            "entities": analysis["entities"],
            "claims": analysis["claims"],
        },
        "latest_analysis_run": analysis["latest_run"],
    }


@router.get("/entities")
def list_entities_endpoint():
    """Return the entity directory for the Phase 3 analyst workbench."""
    from second_brain.analysis.dossier import list_entities
    from second_brain.db import get_db_client

    return list_entities(get_db_client())


@router.get("/entities/{entity_id}")
def get_entity_dossier_endpoint(entity_id: str):
    """Return a Phase 3 dossier with timeline, recent changes, and relationships."""
    from second_brain.analysis.dossier import get_entity_dossier
    from second_brain.db import get_db_client

    try:
        return get_entity_dossier(entity_id, get_db_client())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sources/{source_id}/analyze")
async def analyze_source_endpoint(source_id: str):
    """Run Phase 2 extraction for a single source and return the stored analysis."""
    import asyncio

    def _run():
        from second_brain.analysis.extraction import analyze_source
        from second_brain.db import get_db_client
        from second_brain.providers.llm import get_llm_provider

        db = get_db_client()
        llm = get_llm_provider()
        return analyze_source(source_id, db, llm)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


@router.patch("/conversations/{conversation_id}")
def patch_conversation_endpoint(conversation_id: str, body: ConversationPatch):
    """Update the title of a conversation."""
    from second_brain.chat.conversation import update_title
    update_title(conversation_id, body.title)
    return {"ok": True}


@router.get("/topics")
def list_topics_endpoint():
    """Return all topics sorted by article count descending."""
    from second_brain.db import get_db_client

    db = get_db_client()
    topics = db.table("topics").select("id, name, summary").execute().data or []
    memberships = db.table("source_topics").select("topic_id").execute().data or []

    counts: dict[str, int] = {}
    for row in memberships:
        counts[row["topic_id"]] = counts.get(row["topic_id"], 0) + 1

    result = [
        {
            "id": t["id"],
            "name": t["name"],
            "summary": t.get("summary"),
            "article_count": counts.get(t["id"], 0),
        }
        for t in topics
    ]
    result.sort(key=lambda t: t["article_count"], reverse=True)
    return result


@router.get("/insights")
def list_insights_endpoint():
    """Return all insights ordered newest-first, plus the unseen count.

    Response shape:
      { "insights": [{id, type, title, body, seen, created_at}, ...],
        "unseen_count": int }
    """
    from second_brain.db import get_db_client
    from second_brain.ingestion.insights import get_insights
    db = get_db_client()
    return get_insights(db)


@router.patch("/insights/{insight_id}/seen")
def mark_insight_seen_endpoint(insight_id: str):
    """Mark a single insight as seen (clears the badge count by 1)."""
    from second_brain.db import get_db_client
    from second_brain.ingestion.insights import mark_seen
    db = get_db_client()
    mark_seen(db, insight_id)
    return {"ok": True}


@router.post("/insights/generate-digest")
async def generate_digest_endpoint():
    """Generate a weekly digest from articles ingested in the last 7 days.

    Calls the LLM to synthesize reading themes, then saves the result as a
    'digest' insight row. Returns the new insight or a 'no_articles' status.
    """
    import asyncio

    def _run():
        from second_brain.db import get_db_client
        from second_brain.providers.llm import get_llm_provider
        from second_brain.ingestion.insights import generate_digest
        db = get_db_client()
        llm = get_llm_provider()
        return generate_digest(db, llm)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run)

    if result is None:
        return {"status": "no_articles", "message": "No articles ingested in the last 7 days."}
    return {"status": "ok", "insight": result}


@router.get("/conversations/similar")
def similar_conversations_endpoint(query: str, exclude_id: str):
    """Return past conversations semantically similar to `query`.

    Powers the 'you explored this before' UI nudge in the chat panel.
    Results are shown to the user — they are never injected into LLM prompts.
    """
    from second_brain.chat.memory import retrieve_similar_conversations
    return retrieve_similar_conversations(query, exclude_id)


@router.post("/sync")
async def sync_endpoint():
    """Trigger a Readwise sync from the UI (UI-05).

    Runs sync_readwise() in a thread executor so it doesn't block the event loop.
    The sync can take 30-120s for large corpora; Vercel Hobby allows 300s.

    Returns:
        { "status": "complete" | "error", "message": str }
    """
    import asyncio
    import traceback

    async def run_sync():
        from second_brain.ingestion.readwise import (
            chunk_new_sources,
            fetch_all_articles,
            store_articles,
        )
        from second_brain.config import cfg
        from second_brain.db import get_db_client
        from second_brain.providers.embeddings import get_embedding_provider
        import asyncio

        def _sync():
            db = get_db_client()
            embed = get_embedding_provider()

            # 1. Fetch new articles incrementally (only since last ingested_at)
            from second_brain.ingestion.readwise import get_last_ingested_at
            updated_after = get_last_ingested_at(db)
            logger.info("UI sync: incremental fetch updated_after=%s", updated_after)
            articles = fetch_all_articles(cfg.readwise.token, updated_after=updated_after)
            logger.info("UI sync fetched %s qualifying Readwise articles", len(articles))
            new_count, skipped_count, new_source_ids = store_articles(
                articles,
                db,
                embed_provider=embed,
            )

            # 2. Chunk only the newly inserted articles
            total_chunks = 0
            if new_source_ids:
                total_chunks = chunk_new_sources(
                    new_source_ids,
                    db,
                    embed,
                    target_tokens=cfg.chunking.target_tokens,
                    overlap_tokens=cfg.chunking.overlap_tokens,
                )
                logger.info("UI sync chunked %s new sources → %s chunks", len(new_source_ids), total_chunks)
            else:
                logger.info("UI sync: no new articles, skipping chunking")

            return new_count, skipped_count, total_chunks

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync)

    try:
        new_count, skipped_count, total_chunks = await run_sync()
        return {"status": "complete", "message": f"Sync complete — {new_count} new articles, {skipped_count} already saved, {total_chunks} chunks indexed."}
    except Exception as exc:
        # Log the full traceback server-side; return a safe message to the client
        traceback.print_exc()
        return {"status": "error", "message": f"Sync failed: {exc}"}

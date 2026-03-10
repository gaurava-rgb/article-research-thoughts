"""FastAPI router for chat, conversation management, and sync endpoints.

Endpoints:
  POST   /api/chat                      — stream LLM response as SSE
  POST   /api/conversations             — create new conversation
  GET    /api/conversations             — list conversations (sidebar)
  GET    /api/conversations/{id}/messages — load conversation history
  PATCH  /api/conversations/{id}        — update title

SSE format:
  data: {"type": "token", "content": "<delta>"}\n\n   (one per LLM token)
  data: {"type": "sources", "sources": [...]}\n\n     (after all tokens)
  data: [DONE]\n\n                                     (stream terminator)
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

SYSTEM_PROMPT = (
    "You are a personal knowledge assistant. The user is asking questions about "
    "articles, essays, and ideas they have saved to their Second Brain. "
    "When you have relevant source material, structure your response with "
    "[FROM YOUR SOURCES] for information drawn from their saved articles, "
    "followed by [ANALYSIS] for your synthesis and commentary. "
    "Be concise and specific. Cite article titles when referencing sources."
)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationPatch(BaseModel):
    title: str


@router.post("/chat")
async def chat_endpoint(body: ChatRequest) -> StreamingResponse:
    """Stream an LLM response with SSE, injecting hybrid search context and memory."""
    from second_brain.retrieval.search import hybrid_search, SearchResult
    from second_brain.chat.conversation import (
        get_messages,
        save_message,
        save_message_with_embedding,
        build_messages_for_llm,
    )
    from second_brain.chat.memory import retrieve_memory_context
    from second_brain.config import cfg
    from openai import AsyncOpenAI

    # 1. Retrieve relevant source chunks
    sources: list[SearchResult] = hybrid_search(body.message, top_k=5)
    sources_for_prompt = "\n\n".join(
        f"[Source: {s.source_title}]\n{s.content}" for s in sources
    )
    sources_json = [
        {
            "title": s.source_title,
            "url": s.source_url,
            "author": s.source_author,
            "score": round(s.hybrid_score, 3),
        }
        for s in sources
    ]

    # 2. Cross-session memory (CHAT-04)
    memory_ctx = retrieve_memory_context(body.message, body.conversation_id)

    # 3. Build LLM messages with history (CHAT-01)
    history = get_messages(body.conversation_id)
    history_for_llm = [{"role": m["role"], "content": m["content"]} for m in history]

    full_system = SYSTEM_PROMPT
    if sources_for_prompt:
        full_system += f"\n\nRelevant sources from the user's knowledge base:\n{sources_for_prompt}"

    messages = build_messages_for_llm(
        system_prompt=full_system,
        history=history_for_llm,
        user_message=body.message,
        memory_context=memory_ctx,
    )

    # 4. Save user message
    save_message(body.conversation_id, "user", body.message)

    async def stream_response() -> AsyncGenerator[str, None]:
        client = AsyncOpenAI(
            base_url=cfg.llm.base_url,
            api_key=cfg.llm.api_key,
        )
        full_response = []

        async with client.chat.completions.stream(
            model=cfg.llm.model,
            messages=messages,
        ) as stream:
            async for chunk in stream:
                delta = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if delta:
                    full_response.append(delta)
                    yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

        # 5. Save complete assistant message with embedding (for CHAT-04 future memory)
        complete_response = "".join(full_response)
        if complete_response:
            # Save with embedding in background — fire-and-forget
            asyncio.create_task(
                asyncio.to_thread(
                    save_message_with_embedding,
                    body.conversation_id,
                    "assistant",
                    complete_response,
                )
            )

        # 6. Send sources event then DONE
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_json})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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


@router.patch("/conversations/{conversation_id}")
def patch_conversation_endpoint(conversation_id: str, body: ConversationPatch):
    """Update the title of a conversation."""
    from second_brain.chat.conversation import update_title
    update_title(conversation_id, body.title)
    return {"ok": True}

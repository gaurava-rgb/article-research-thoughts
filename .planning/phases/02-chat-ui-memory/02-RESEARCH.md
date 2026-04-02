# Phase 2: Chat UI + Memory — Research

**Researched:** 2026-03-10
**Domain:** Next.js 15 frontend + FastAPI chat API + conversation persistence + cross-session memory
**Confidence:** HIGH (core stack decisions locked; research verifies implementation paths)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Chat interface with message bubbles and markdown rendering | Next.js 15 + react-markdown or streamdown; message bubble layout via Tailwind + shadcn |
| UI-02 | Source citations rendered as expandable cards (click to see original article) | Custom CitationCard component; sources returned as structured JSON alongside streamed text |
| UI-03 | Visual distinction between [FROM SOURCES] and [ANALYSIS] content | LLM prompt + structured response markers; Tailwind CSS color differentiation |
| UI-04 | Conversation sidebar showing past chats | shadcn Sidebar component; Supabase conversations table read on load |
| UI-05 | Source ingestion panel — paste URL or trigger Readwise sync | POST /api/sync endpoint wrapping existing sync CLI logic; UI panel in Next.js |
| UI-07 | Frontend deployed to Vercel | Next.js + FastAPI on Vercel via vercel.json; api/ directory pattern |
| CHAT-01 | Multi-turn conversation — follow-up questions reference prior turns | Conversation history injected into LLM context window; messages stored per conversation_id |
| CHAT-02 | Past conversations stored and listed in sidebar | Supabase conversations + messages tables; GET /api/conversations endpoint |
| CHAT-03 | User can load and continue a past conversation | GET /api/conversations/{id}/messages; frontend loads history into chat state |
| CHAT-04 | Cross-session memory — system recalls relevant past conversations | Past assistant messages embedded and stored; semantic search over message history before each response |
</phase_requirements>

---

## Summary

Phase 2 builds the browser-facing layer for this system: a Next.js 15 App Router frontend deployed to Vercel, connected to FastAPI endpoints that wrap the existing hybrid retrieval pipeline. The frontend is built with shadcn/ui + Tailwind CSS v4, using a streaming SSE connection to receive LLM responses token-by-token. The backend gains a `/api/chat` streaming endpoint, conversation CRUD endpoints, and a `/api/sync` trigger endpoint.

The most important architectural decision is how the Next.js frontend and FastAPI backend are co-deployed on Vercel. Vercel's official Next.js + FastAPI starter demonstrates the canonical approach: FastAPI lives at `api/index.py` in the repo root, Next.js frontend lives in standard structure, and a `vercel.json` rewrites `/api/*` to the FastAPI function. Both deploy in the same `vercel deploy` command. This eliminates CORS complexity entirely in production (same origin). For local dev, `concurrently` runs both on different ports and Next.js proxies `/api/*` to FastAPI via `next.config.js`.

Cross-session memory (CHAT-04) is implemented with a lightweight approach that fits this project's scale: after each conversation, the final assistant response is embedded and stored; on new queries, semantic search is run against past message content to find relevant prior conversations that are injected as context summaries. This avoids third-party memory libraries and reuses the existing `hybrid_search` / embedding infrastructure already built in Phase 1.

**Primary recommendation:** Build with Next.js 15 App Router + shadcn/ui + Tailwind v4. Stream responses via SSE from FastAPI using `StreamingResponse(media_type="text/event-stream")`. Use the Vercel Next.js + FastAPI monorepo pattern. Implement cross-session memory by embedding and retrieving past assistant messages.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.x | React framework, routing, SSR | Locked decision; deploys to Vercel natively |
| React | 19.x | UI runtime | Bundled with Next.js 15 |
| TypeScript | 5.x | Type safety | Standard with Next.js 15 starter |
| Tailwind CSS | 4.x | Utility CSS | shadcn/ui requires it; v4 is current as of 2025 |
| shadcn/ui | latest | Component library (Sidebar, Button, Card, ScrollArea) | Industry standard for Next.js 15 apps; includes Sidebar component for conversation list |
| react-markdown | 9.x | Render LLM markdown responses | Standard library; used in Vercel AI SDK cookbook |
| remark-gfm | 4.x | GitHub-flavored markdown (tables, task lists) | Paired with react-markdown; needed for formatted responses |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| streamdown | latest | Drop-in react-markdown replacement for streaming | Use if react-markdown re-render jank is noticeable; handles incomplete tokens gracefully |
| highlight.js or shiki | latest | Code block syntax highlighting | Use when LLM returns code blocks (likely in a knowledge base context) |
| concurrently | 9.x | Run Next.js dev + FastAPI dev in one terminal | Dev only; `npm run dev` starts both servers |
| @types/node | 22.x | TypeScript Node types | Needed for Next.js server config |

### FastAPI Backend Additions (Phase 2)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.115.x | Chat + sync API endpoints | Already used; extend with new routes |
| uvicorn | 0.32.x | ASGI server | Standard FastAPI runner |
| python-dotenv | 1.x | Load .env in local dev | Standard; Vercel handles env vars in production |
| asyncio / AsyncOpenAI | openai 1.x | Streaming LLM responses | openai library already in pyproject.toml; use AsyncOpenAI for async streaming |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-markdown | Vercel AI SDK useChat | AI SDK couples frontend to Vercel's stream protocol; adds abstraction cost; this project has a custom FastAPI backend where plain SSE + fetch is simpler and more transparent |
| shadcn/ui | Chakra UI, Radix primitives directly | shadcn/ui is unstyled-first but opinionated enough to avoid building from scratch; Chakra adds a heavier runtime |
| Manual SSE fetch | EventSource API | EventSource doesn't support POST requests; manual fetch with ReadableStream is required for chat (POST with message body) |
| streamdown | react-markdown | react-markdown works fine if updates are rate-limited; switch to streamdown only if visible re-render jank occurs |

### Installation

```bash
# Frontend
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
cd frontend
npx shadcn@latest init
npx shadcn@latest add sidebar button card scroll-area textarea separator badge
npm install react-markdown remark-gfm
npm install -D concurrently

# Backend additions
cd ../backend
pip install "fastapi>=0.115" "uvicorn[standard]>=0.32" python-dotenv
```

---

## Architecture Patterns

### Recommended Project Structure

```
/                               # repo root
├── api/
│   └── index.py               # FastAPI app entrypoint (Vercel requirement)
├── backend/
│   └── second_brain/          # existing Python package
│       ├── chat/              # NEW: chat module
│       │   ├── __init__.py
│       │   ├── router.py      # FastAPI router: /chat, /conversations, /sync
│       │   ├── conversation.py # conversation + message CRUD
│       │   └── memory.py      # cross-session memory retrieval
│       ├── providers/         # existing
│       ├── retrieval/         # existing
│       └── ingestion/         # existing
├── frontend/                  # Next.js app
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx       # root redirects to /chat
│   │   │   └── chat/
│   │   │       ├── page.tsx   # main chat page (new conversation)
│   │   │       └── [id]/
│   │   │           └── page.tsx  # load existing conversation
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx      # message list + input
│   │   │   ├── MessageBubble.tsx  # user/assistant bubble + markdown
│   │   │   ├── CitationCard.tsx   # expandable source card
│   │   │   ├── ConvSidebar.tsx    # conversation history sidebar
│   │   │   └── IngestionPanel.tsx # sync trigger UI
│   │   └── lib/
│   │       ├── api.ts          # typed API client (fetch wrappers)
│   │       └── types.ts        # shared TypeScript types
│   ├── next.config.ts
│   └── package.json
├── vercel.json                # routes /api/* to FastAPI, /* to Next.js
├── schema.sql                 # existing
└── config.yaml                # existing
```

### Pattern 1: FastAPI StreamingResponse for Chat

**What:** FastAPI endpoint receives message + conversation_id, retrieves context via hybrid_search, builds prompt with history, streams LLM response token by token as SSE.

**When to use:** Every chat message submission.

**Example:**
```python
# backend/second_brain/chat/router.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
import json

router = APIRouter()

async def stream_chat_response(messages: list[dict], sources: list[dict]):
    """Async generator: yields SSE chunks then a final sources event."""
    client = AsyncOpenAI(
        base_url=cfg.llm.base_url,
        api_key=cfg.llm.api_key,
    )
    async with client.chat.completions.stream(
        model=cfg.llm.model,
        messages=messages,
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                # SSE format: data: <content>\n\n
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
    # After all tokens, send sources as a final event
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/chat")
async def chat(body: ChatRequest):
    sources = retrieve_context(body.message)
    messages = build_messages(body.conversation_id, body.message, sources)
    return StreamingResponse(
        stream_chat_response(messages, sources),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### Pattern 2: Next.js SSE Consumer (fetch + ReadableStream)

**What:** Frontend POSTs to `/api/chat`, reads the SSE stream using `response.body.getReader()`, accumulates tokens, extracts sources from the final event.

**When to use:** Every message send in the chat UI.

**Example:**
```typescript
// frontend/src/lib/api.ts
export async function sendMessage(
  conversationId: string,
  message: string,
  onToken: (token: string) => void,
  onSources: (sources: Source[]) => void,
) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split("\n\n");
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.replace("data: ", "");
      if (raw === "[DONE]") return;
      const event = JSON.parse(raw);
      if (event.type === "token") onToken(event.content);
      if (event.type === "sources") onSources(event.sources);
    }
  }
}
```

### Pattern 3: Vercel Deployment (vercel.json)

**What:** Single vercel.json routes `/api/*` to the FastAPI function, everything else to Next.js.

**When to use:** Production Vercel deployment (this is the official pattern).

**Example:**
```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "/api/index" }
  ]
}
```

The FastAPI app at `api/index.py` imports the router and mounts it at the app level. In local development, Next.js `next.config.ts` proxies `/api/*` to `http://localhost:8000`.

### Pattern 4: Conversation CRUD (Supabase Python client)

**What:** Thin CRUD layer over the `conversations` and `messages` tables already defined in `schema.sql`.

**When to use:** Creating conversations, loading history, listing sidebar entries.

**Example:**
```python
# backend/second_brain/chat/conversation.py
from second_brain.db import get_db_client

def create_conversation(title: str | None = None) -> dict:
    db = get_db_client()
    result = db.table("conversations").insert({"title": title}).execute()
    return result.data[0]

def list_conversations(limit: int = 50) -> list[dict]:
    db = get_db_client()
    result = (
        db.table("conversations")
        .select("id, title, created_at, updated_at")
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data

def get_messages(conversation_id: str) -> list[dict]:
    db = get_db_client()
    result = (
        db.table("messages")
        .select("id, role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data

def save_message(conversation_id: str, role: str, content: str) -> dict:
    db = get_db_client()
    result = db.table("messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
    }).execute()
    # Update conversation updated_at
    db.table("conversations").update({"updated_at": "now()"}).eq("id", conversation_id).execute()
    return result.data[0]
```

### Pattern 5: Cross-Session Memory (CHAT-04)

**What:** Before answering, search past assistant messages semantically for related conversations. Inject top matches as a memory context block in the system prompt.

**When to use:** Every chat request (lightweight — just a second hybrid_search call over `messages` table content).

**Implementation:**

The `messages` table exists in `schema.sql` but currently has no embedding column. Phase 2 adds an `embedding vector(1536)` column to `messages` and an IVFFlat index to enable semantic search over past responses.

Schema addition (append to schema.sql as idempotent ALTER):
```sql
-- Phase 2 addition: embeddings on messages for cross-session memory
ALTER TABLE messages ADD COLUMN IF NOT EXISTS embedding vector(1536);
CREATE INDEX IF NOT EXISTS messages_embedding_idx
  ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

Memory retrieval in Python:
```python
# backend/second_brain/chat/memory.py
def retrieve_memory_context(query: str, current_conversation_id: str, top_k: int = 3) -> str:
    """
    Semantic search over past assistant messages to find related conversations.
    Returns a formatted string injected into the system prompt.
    """
    from second_brain.db import get_db_client
    from second_brain.providers.embeddings import get_embedding_provider

    embedding = get_embedding_provider().embed([query])[0]
    db = get_db_client()

    response = db.rpc("search_past_messages", {
        "query_embedding": embedding,
        "exclude_conversation_id": current_conversation_id,
        "match_count": top_k,
    }).execute()

    if not response.data:
        return ""

    lines = ["[PAST CONVERSATIONS — use these to answer 'we discussed...' questions]"]
    for row in response.data:
        lines.append(f"- Conversation '{row['conv_title']}' ({row['created_at'][:10]}): {row['content'][:200]}")
    return "\n".join(lines)
```

A `search_past_messages` SQL function (similar to `hybrid_search`) is added to schema.sql.

### Pattern 6: Conversation Auto-Title

**What:** After the first user message, call the LLM with a one-shot prompt to generate a 5-7 word title. Store it in `conversations.title`.

**When to use:** On the second message in a conversation (first response received), in the background (non-blocking).

**Why:** "we discussed this in a March session" (CHAT-04) requires conversations to have meaningful titles.

**Example prompt:**
```
Given this first message: "{first_message}"
Generate a concise 5–7 word title for this conversation. Return only the title, no punctuation.
```

### Anti-Patterns to Avoid

- **Using EventSource for chat:** EventSource only supports GET requests. Chat requires POST (message body). Always use `fetch` + `ReadableStream`.
- **Injecting full conversation history into every prompt:** For long conversations this burns context window. Inject last N messages (e.g., last 10 turns) plus a summary of earlier turns if needed.
- **Storing raw embedding vectors in messages table without an index:** The ALTER TABLE must include the IVFFlat index or semantic search will be a full table scan.
- **SSE buffering at proxy/nginx layer:** Set `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers on all streaming responses. Vercel handles this correctly; be careful with local proxies.
- **Hardcoding the backend URL in Next.js client components:** Use `NEXT_PUBLIC_API_URL` environment variable. On Vercel, set this to the same domain (since `/api/*` routes to FastAPI function). In development, set it to `http://localhost:8000`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom HTML renderer | react-markdown + remark-gfm | Edge cases: nested lists, code blocks, tables, XSS — hundreds of hours of community fixes |
| Streaming token accumulation | Custom SSE parser | fetch + ReadableStream decoder pattern (3 lines) | TextDecoder + ReadableStream handles UTF-8 boundaries correctly |
| UI component primitives | Custom Button, Input, Card, Sidebar | shadcn/ui | Accessibility, keyboard navigation, focus management — correctness is hard; shadcn is proven |
| Conversation list sorting | Custom date-sort logic | Supabase `.order("updated_at", desc=True)` | DB-level ordering is correct and index-backed |
| LLM context window management | Custom token counter | Pass last 10 messages; tiktoken if precise counting needed | Simple message count limit (last 10) covers most conversations without complexity |

**Key insight:** The hardest bugs in chat interfaces are SSE buffering (proxy strips newlines), React re-render thrash during streaming (fix: memoize the rendered markdown), and context window overflow. Don't invent solutions — use the patterns above.

---

## Common Pitfalls

### Pitfall 1: SSE Streams Buffered by Proxy / Nginx

**What goes wrong:** Streaming appears to work locally but on Vercel (or behind any reverse proxy) the entire response arrives at once, ruining the streaming UX.

**Why it happens:** Some proxies buffer responses until they see the Content-Length header or the connection closes.

**How to avoid:** Always set `Cache-Control: no-cache` and `X-Accel-Buffering: no` on the FastAPI StreamingResponse headers. Vercel respects these. Test streaming behavior on Vercel deploy early (Wave 1), not just locally.

**Warning signs:** Response arrives all at once in the browser; 0-byte events during transfer.

### Pitfall 2: React Re-Render Thrash During Streaming

**What goes wrong:** react-markdown re-parses and re-renders the entire message on every token, causing visible stutter with long responses.

**Why it happens:** react-markdown is not streaming-optimized; the full content string is passed as a prop and re-rendered on every state update.

**How to avoid:** Memoize the completed portion. Only the "in-progress last paragraph" should re-render on each token. Alternatively use streamdown which handles this natively. The Vercel AI SDK cookbook documents this exact memoization pattern.

**Warning signs:** CPU usage spikes during streaming; visible re-render flicker in long responses.

### Pitfall 3: CORS Errors in Development

**What goes wrong:** Browser blocks Next.js (port 3000) fetching from FastAPI (port 8000) in local dev.

**Why it happens:** Same-origin policy; different ports = different origins.

**How to avoid:** Add CORSMiddleware to FastAPI allowing `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`. In production on Vercel this doesn't apply because both are on the same domain.

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-vercel-domain.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Warning signs:** Browser console shows "CORS policy: No 'Access-Control-Allow-Origin' header".

### Pitfall 4: FastAPI Startup Cost on Vercel (Cold Starts)

**What goes wrong:** First request after inactivity takes 3–8 seconds as the Python function cold-starts. The LLM response doesn't begin until after cold start.

**Why it happens:** Vercel serverless functions spin down when idle; Python imports take time.

**How to avoid:** Keep imports lazy (same pattern already established in Phase 1). Don't import `config.py` at module level in `api/index.py` — config loads env vars at import which is slow. Use the existing lazy-import pattern: import inside route handlers. Keep `pyproject.toml` dependencies minimal.

**Warning signs:** First request timeout in Vercel logs; subsequent requests fast.

### Pitfall 5: Missing `embedding` Column on `messages` Table in Production

**What goes wrong:** CHAT-04 cross-session memory fails silently — `search_past_messages` RPC returns empty results.

**Why it happens:** The ALTER TABLE to add `embedding` to `messages` was applied locally but not in the production Supabase instance.

**How to avoid:** Phase 2 plan must explicitly include "apply schema additions to Supabase" as a verification step. Make the ALTER idempotent with `ADD COLUMN IF NOT EXISTS`.

**Warning signs:** Memory retrieval always returns empty string; no errors logged (the RPC simply returns nothing).

### Pitfall 6: Conversation History Context Window Overflow

**What goes wrong:** Long conversations cause LLM to receive a prompt that exceeds its context window, causing API errors or truncation.

**Why it happens:** Injecting full message history + retrieved chunks + system prompt + user message.

**How to avoid:** Cap injected history at last 10 messages (20 turns). For very long conversations, optionally summarize older turns. Start with the cap; add summarization only if needed.

**Warning signs:** OpenRouter API returns 400/context-length error; response quality degrades on long conversations.

---

## Code Examples

Verified patterns from official/authoritative sources:

### FastAPI StreamingResponse (SSE)

```python
# Source: FastAPI official SSE docs + sevalla.com verified pattern
from fastapi.responses import StreamingResponse

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for chunk in llm_stream():
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

### Next.js fetch SSE Consumer

```typescript
// Source: Upstash SSE blog post (verified pattern)
const response = await fetch("/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value, { stream: true });
  // Process SSE lines
  for (const line of text.split("\n")) {
    if (line.startsWith("data: ")) {
      const data = line.slice(6);
      if (data !== "[DONE]") setContent(prev => prev + JSON.parse(data).content);
    }
  }
}
```

### shadcn/ui Sidebar (conversation list)

```typescript
// Source: shadcn/ui docs + Next.js 15 starter
import { Sidebar, SidebarContent, SidebarMenu, SidebarMenuItem } from "@/components/ui/sidebar";

export function ConvSidebar({ conversations, currentId }: Props) {
  return (
    <Sidebar>
      <SidebarContent>
        <SidebarMenu>
          {conversations.map(conv => (
            <SidebarMenuItem key={conv.id}>
              <Link href={`/chat/${conv.id}`} className={conv.id === currentId ? "font-bold" : ""}>
                {conv.title ?? "Untitled conversation"}
              </Link>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
    </Sidebar>
  );
}
```

### react-markdown with source content

```typescript
// Source: react-markdown README + Vercel AI SDK cookbook
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { memo } from "react";

const MemoizedMarkdown = memo(({ content }: { content: string }) => (
  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
));
// Memoize to prevent re-render on each streaming token for completed messages
```

### vercel.json for Next.js + FastAPI

```json
// Source: Vercel Next.js FastAPI Starter template (official Vercel)
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "/api/index" }
  ]
}
```

### next.config.ts local dev proxy

```typescript
// Source: Next.js official docs + Next.js FastAPI Starter
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};
export default nextConfig;
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vercel AI SDK `useChat` with custom Python backends | Plain fetch + ReadableStream + SSE; AI SDK optional for complex use cases | Ongoing — AI SDK v5 data protocol issues with FastAPI reported in 2025 | Use plain fetch/SSE for FastAPI; less abstraction, more control |
| react-markdown (standard) | streamdown for streaming specifically | 2024–2025 | Either works; streamdown is streaming-optimized |
| tailwind.config.js | Tailwind v4 uses CSS-based config (no JS config file) | Tailwind v4 (2025) | Initialization changed — shadcn/ui CLI handles this automatically |
| Separate `pages/api/` routes for FastAPI proxy | `vercel.json` rewrites to FastAPI function | 2023+ | Cleaner monorepo; no Node.js shim layer needed |

**Deprecated/outdated:**
- `pages/api/` directory: This project uses App Router; avoid `pages/api/`. All API calls go directly to FastAPI via `vercel.json` rewrites.
- `next-connect` middleware: Not needed with App Router Route Handlers.
- `tailwind.config.js`: Tailwind v4 uses CSS imports; shadcn init handles migration automatically.

---

## Open Questions

1. **Backend deployment: Vercel serverless vs. always-on**
   - What we know: FastAPI on Vercel works and is the path of least resistance for UI-07 (Vercel deploy). Vercel Hobby plan has 300s max duration, which is sufficient for LLM streaming. Cold starts are a nuisance but not blocking.
   - What's unclear: Whether cold start latency (3–8s for Python) is acceptable UX for this personal tool.
   - Recommendation: Start with Vercel serverless (simpler). If cold starts are annoying, migrate FastAPI to Railway/Render (always-on) while keeping Next.js on Vercel. Scope that as a possible out-of-phase improvement.

2. **NEXT_PUBLIC_API_URL value on Vercel**
   - What we know: In production, since `/api/*` is handled by the FastAPI Vercel function on the same domain, the API URL is just `/api` (relative). No `NEXT_PUBLIC_API_URL` env var needed in production.
   - What's unclear: Whether the initial frontend calls during Vercel's build step need the variable.
   - Recommendation: Use relative `/api` prefix for all fetch calls. Set `NEXT_PUBLIC_API_URL=""` (empty) so the code `${process.env.NEXT_PUBLIC_API_URL}/api/chat` works in both environments.

3. **Conversation auto-title timing**
   - What we know: Generating a title requires an LLM call, which adds latency.
   - What's unclear: Whether to generate synchronously (blocks the first response) or asynchronously (fire-and-forget after first response).
   - Recommendation: Fire-and-forget using `asyncio.create_task()` after the first LLM response completes. The sidebar refreshes the title on next load.

---

## Validation Architecture

> `workflow.nyquist_validation` not present in config — validation section included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (already in pyproject.toml dev deps) |
| Config file | `backend/pytest.ini` or `backend/pyproject.toml [tool.pytest.ini_options]` — Wave 0 gap |
| Quick run command | `cd backend && pytest tests/chat/ -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

Note: No frontend test framework is scoped for this phase. The Phase 2 requirements are functionally verified by running the app (UI-07: Vercel deploy is a deploy step, not a test). Backend logic (conversation CRUD, memory retrieval, streaming) is unit-testable.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | Multi-turn context: messages from prior turns injected in LLM prompt | unit | `pytest tests/chat/test_conversation.py::test_build_messages_injects_history -x` | Wave 0 |
| CHAT-02 | Past conversations listed in correct order | unit | `pytest tests/chat/test_conversation.py::test_list_conversations_ordered -x` | Wave 0 |
| CHAT-03 | Load conversation returns messages in order | unit | `pytest tests/chat/test_conversation.py::test_get_messages_ordered -x` | Wave 0 |
| CHAT-04 | Memory search returns relevant past turns | unit | `pytest tests/chat/test_memory.py::test_retrieve_memory_context -x` | Wave 0 |
| UI-01 | Chat endpoint returns SSE stream | integration | `pytest tests/chat/test_router.py::test_chat_streams_sse -x` | Wave 0 |
| UI-05 | Sync endpoint triggers ingestion | integration | manual (requires live READWISE_TOKEN) | manual-only |
| UI-07 | Frontend deployed to Vercel | deploy | `vercel deploy --prebuilt` succeeds | manual step |

### Sampling Rate

- Per task commit: `cd backend && pytest tests/chat/ -x -q`
- Per wave merge: `cd backend && pytest -x -q`
- Phase gate: Full suite green before marking Phase 2 complete

### Wave 0 Gaps

- [ ] `backend/tests/chat/__init__.py` — test package marker
- [ ] `backend/tests/chat/test_conversation.py` — covers CHAT-01, CHAT-02, CHAT-03
- [ ] `backend/tests/chat/test_memory.py` — covers CHAT-04
- [ ] `backend/tests/chat/test_router.py` — covers UI-01 (SSE streaming)
- [ ] `backend/pytest.ini` — configure asyncio mode: `asyncio_mode = auto`
- [ ] Framework already installed (pytest + pytest-asyncio in pyproject.toml dev deps) — no new install needed

---

## Sources

### Primary (HIGH confidence)

- Vercel FastAPI deployment docs: https://vercel.com/docs/frameworks/backend/fastapi — FastAPI on Vercel deployment requirements, entrypoint file paths, bundle size limits
- Vercel Functions Limitations: https://vercel.com/docs/functions/limitations — 300s max duration, 500MB bundle limit, 4.5MB payload limit
- Vercel Next.js FastAPI Starter: https://vercel.com/templates/next.js/nextjs-fastapi-starter — monorepo pattern, vercel.json structure
- Vercel AI SDK Stream Protocol docs: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol — x-vercel-ai-ui-message-stream header, TextStreamChatTransport
- FastAPI official SSE tutorial: https://fastapi.tiangolo.com/tutorial/server-sent-events/ — StreamingResponse with text/event-stream
- react-markdown GitHub: https://github.com/remarkjs/react-markdown — API, plugins

### Secondary (MEDIUM confidence)

- Upstash SSE streaming blog (verified against FastAPI + Next.js patterns): https://upstash.com/blog/sse-streaming-llm-responses
- Vercel AI SDK markdown chatbot cookbook: https://ai-sdk.dev/cookbook/next/markdown-chatbot-with-memoization — memoization pattern for streaming markdown
- Streamdown library for streaming AI markdown: https://streamdown.ai — drop-in react-markdown replacement for streaming
- FastAPI CORS official docs: https://fastapi.tiangolo.com/tutorial/cors/ — CORSMiddleware configuration
- Cross-session memory architecture survey (mgx.dev): https://mgx.dev/insights/cross-session-agent-memory-foundations-implementations-challenges-and-future-directions — memory retrieval patterns

### Tertiary (LOW confidence)

- shadcn/ui Tailwind v4 compatibility (medium-to-high; official docs state v4 compatible): https://ui.shadcn.com/docs/tailwind-v4
- Cold start latency estimates (3–8s) for Python on Vercel: from community reports; exact numbers vary by bundle size

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — Next.js + shadcn + FastAPI + Vercel are locked decisions; react-markdown and SSE patterns are verified against official docs
- Architecture: HIGH — Vercel Next.js + FastAPI monorepo pattern is documented with an official Vercel starter template
- Chat streaming: HIGH — FastAPI StreamingResponse SSE + fetch ReadableStream pattern is verified across multiple authoritative sources
- Cross-session memory (CHAT-04): MEDIUM — The embedding-based approach is sound and reuses existing infrastructure, but the exact `search_past_messages` SQL function and messages.embedding column design are novel to this project
- Pitfalls: HIGH — SSE buffering, react-markdown re-render, CORS, cold starts are all well-documented issues in this stack

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (Next.js and shadcn release frequently; re-verify shadcn CLI commands if > 30 days old)

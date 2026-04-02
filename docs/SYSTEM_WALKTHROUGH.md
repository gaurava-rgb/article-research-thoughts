# Second Brain — Complete End-to-End System Walkthrough

How the system works from moment one to final output: every component, every API call, every database hit.

---

## High-Level Overview

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐
│  Readwise    │────▶│  Backend     │────▶│  Supabase    │◀────│  Frontend │
│  Reader API  │     │  (FastAPI)   │────▶│  (Postgres   │     │  (Next.js)│
└─────────────┘     │  + CLI       │     │  + pgvector) │     └───────────┘
                    │              │────▶│              │
                    └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  OpenRouter  │
                    │  (LLM +     │
                    │  Embeddings) │
                    └──────────────┘
```

Three main flows:
1. **Sync Flow** — Pull articles from Readwise → chunk → embed → store in Supabase
2. **Chat Flow** — User asks question → hybrid search → LLM generates answer with sources
3. **Topic Assignment** — Group sources into auto-named topics via embeddings + LLM

---

## External Services

| Service | What it does | API endpoint | Auth |
|---------|-------------|--------------|------|
| **Readwise Reader** | Source of all articles/highlights | `GET https://readwise.io/api/v3/list/` | `Authorization: Token {READWISE_TOKEN}` |
| **OpenRouter** (Embeddings) | Generates 1536-dim vectors | OpenAI-compatible endpoint at `cfg.embeddings.base_url` | `Authorization: Bearer {OPENROUTER_API_KEY}` |
| **OpenRouter** (LLM) | Chat completions for Q&A + topic naming | OpenAI-compatible endpoint at `cfg.llm.base_url` | `Authorization: Bearer {OPENROUTER_API_KEY}` |
| **Supabase** | PostgreSQL database + pgvector for vector search | Project URL from `SUPABASE_URL` | `SUPABASE_KEY` (anon or service key) |

### Models Used
- **Embeddings**: `openai/text-embedding-3-small` via OpenRouter — outputs **1536 dimensions**
- **LLM**: `meta-llama/llama-3.1-8b-instruct` via OpenRouter

### Environment Variables Required
| Variable | Used by | Purpose |
|----------|---------|---------|
| `READWISE_TOKEN` | readwise.py | Authenticate with Readwise Reader API |
| `SUPABASE_URL` | db.py | Supabase project URL |
| `SUPABASE_KEY` | db.py | Supabase anon/service key |
| `OPENROUTER_API_KEY` | embeddings.py, llm.py | Authenticate with OpenRouter for both embedding + LLM calls |

Loaded via: `.env` file at project root → `python-dotenv` with `override=True` in `config.py` → config YAML resolves `_env` suffixed fields to actual env var values.

---

## Database Schema (Supabase/PostgreSQL + pgvector)

File: `schema.sql`

### Tables

#### `sources` — One row per ingested article
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | Auto-generated |
| `readwise_id` | TEXT (UNIQUE) | Dedup key — prevents re-ingesting same article |
| `title` | TEXT | Article title |
| `author` | TEXT | Nullable |
| `url` | TEXT | Nullable |
| `source_type` | TEXT | Default `'readwise_reader'` |
| `published_at` | TIMESTAMPTZ | When the article was originally published |
| `ingested_at` | TIMESTAMPTZ | When we fetched it |
| `raw_text` | TEXT | Full article text (used for chunking + FTS) |
| `source_embedding` | vector(1536) | Whole-article embedding (used for topic clustering) |

#### `chunks` — Chunked pieces of each article (for retrieval)
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | Auto-generated |
| `source_id` | UUID (FK → sources) | Which article this chunk belongs to |
| `chunk_index` | INTEGER | 0-based position within article |
| `content` | TEXT | The chunk text |
| `token_count` | INTEGER | Token count via tiktoken |
| `embedding` | vector(1536) | Chunk embedding (used in hybrid search) |

**Indexes on chunks:**
- IVFFlat index on `embedding` (cosine ops, 100 lists) — fast vector similarity search
- GIN index on `to_tsvector('english', content)` — full-text search

#### `conversations` — Chat sessions
| Column | Type |
|--------|------|
| `id` | UUID (PK) |
| `title` | TEXT (nullable) |
| `created_at` | TIMESTAMPTZ |
| `updated_at` | TIMESTAMPTZ |

#### `messages` — Individual chat messages
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | |
| `conversation_id` | UUID (FK → conversations) | |
| `role` | TEXT | `'user'` or `'assistant'` (CHECK constraint) |
| `content` | TEXT | Message text |
| `embedding` | vector(1536) | For cross-session memory search |
| `created_at` | TIMESTAMPTZ | |

**Index on messages:** IVFFlat on `embedding` (cosine ops, 50 lists)

#### `topics` — Auto-generated topic clusters (Phase 3)
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | |
| `name` | TEXT | LLM-generated 2-6 word name |
| `summary` | TEXT | Nullable (not yet implemented) |
| `centroid_embedding` | vector(1536) | Mean of all member source embeddings, normalized |

#### `source_topics` — Many-to-many join
| Column | Type |
|--------|------|
| `source_id` | UUID (FK → sources) |
| `topic_id` | UUID (FK → topics) |
| PK = (source_id, topic_id) | |

### SQL Functions (stored in Supabase)

| Function | Purpose | Called by |
|----------|---------|----------|
| `hybrid_search(query_embedding, query_text, match_count, date_after, date_before)` | Vector similarity (cosine) + FTS (ts_rank), weighted 70/30, returns top-K chunks with source metadata | `retrieval/search.py` |
| `search_past_messages(query_embedding, exclude_conversation_id, match_count)` | Find similar past assistant messages for cross-session memory | `chat/memory.py` |
| `match_topic(query_embedding, match_threshold, match_count)` | Find closest topic by centroid similarity | `ingestion/clustering.py` |

---

## Flow 1: Sync (Readwise → Database)

Triggered by: `second-brain sync` CLI command or `POST /api/sync` from frontend.

### Step 1 — Fetch new articles from Readwise (incremental)

**File:** `ingestion/readwise.py` → `fetch_all_articles(token, updated_after=None)`

```
API call:  GET https://readwise.io/api/v3/list/?withHtmlContent=true&updatedAfter={iso_ts}&pageCursor={cursor}
Header:    Authorization: Token {READWISE_TOKEN}
Response:  { "count": N, "nextPageCursor": "..." | null, "results": [...] }
```

- Before fetching, queries `MAX(ingested_at)` from the `sources` table
- Passes `updatedAfter={last_ingested_at}` to the Readwise API — only articles added/modified since then are returned
- On a first-run (empty DB), `updatedAfter` is omitted and all articles are fetched
- Uses **pageCursor-based pagination** (not offset — offset can miss articles)
- Loops until `nextPageCursor` is null
- For each article result:
  - Extracts text: prefers `content` field (plain text), falls back to `html_content` (parsed via custom `HTMLParser`)
  - Filters out articles with < 50 chars of text (MIN_TEXT_LENGTH)
  - Creates a `ReadwiseArticle` dataclass with: readwise_id, title, author, url, published_at, text, ingested_at

**API calls made:** On incremental runs (e.g. 5 new articles), typically 1-2 calls. On first run (full corpus), ~25-38 calls.

**Output:** List of `ReadwiseArticle` objects — only new/updated articles

> **Previous behaviour (fixed):** The old code fetched all articles unconditionally, then discarded already-stored ones in `store_articles()`. For 757 articles with 43 new, this wasted ~36 Readwise API calls fetching 714 articles that were immediately skipped. The `updatedAfter` param fixes this.

---

### Step 2 — Store new articles + source embeddings

**File:** `ingestion/readwise.py` → `store_articles(articles, db, embed_provider)`

For each article:

1. **Dedup check** — Query Supabase:
   ```
   DB call:  SELECT id FROM sources WHERE readwise_id = '{article.readwise_id}'
   ```
   If found → skip (already ingested).

2. **Generate source-level embedding** — API call to OpenRouter:
   ```
   API call:  POST {embeddings_base_url}/embeddings
   Body:      { "model": "openai/text-embedding-3-small", "input": [truncated_text] }
   ```
   - Text is truncated to 8,000 tokens max (via tiktoken `cl100k_base` encoding)
   - Returns: 1536-dim float vector

3. **Insert into sources table** — DB call:
   ```
   DB call:  INSERT INTO sources (title, author, url, published_at, ingested_at, readwise_id, raw_text, source_embedding) VALUES (...)
   ```
   - Handles race condition: if duplicate `readwise_id` error (code 23505), skip gracefully

**API calls made:** 1 embedding call per NEW article (skipped articles = 0 API calls)

**DB calls made:** 1 SELECT + 1 INSERT per article (2 per article)

**Output:** (new_count, skipped_count) — e.g., (43 new, 714 skipped)

---

### Step 3 — Chunk and embed new articles

**File:** `ingestion/readwise.py` → `backfill_missing_chunks(db, embed_provider, target_tokens, overlap_tokens)`

First, finds sources that have `raw_text` but zero rows in the `chunks` table:
```
DB call:  SELECT id, readwise_id, title, raw_text FROM sources
DB call:  SELECT source_id FROM chunks
→ diff = sources with no chunks
```

For each unchunked source:

1. **Chunk the text** — `ingestion/chunker.py` → `chunk_text(raw_text, source_id, target_tokens=500, overlap_tokens=50)`
   - Split text into sentences (regex on `.`, `!`, `?`, and double newlines)
   - Accumulate sentences until buffer hits ~500 tokens
   - Save buffer as a `Chunk`, seed next buffer with last 50 tokens of overlap
   - Drop chunks < 20 tokens (MIN_CHUNK_TOKENS)
   - Token counting: tiktoken `cl100k_base` encoding
   - **No API calls** — pure local computation

2. **Embed all chunks** — `ingestion/chunker.py` → `store_chunks_with_embeddings(chunks, embed_provider, db)`
   - Batches chunks into groups of 100
   - For each batch:
     ```
     API call:  POST {embeddings_base_url}/embeddings
     Body:      { "model": "openai/text-embedding-3-small", "input": [chunk1, chunk2, ...up to 100] }
     ```
   - Returns: list of 1536-dim vectors

3. **Store each chunk** — DB call per chunk:
   ```
   DB call:  INSERT INTO chunks (source_id, chunk_index, content, token_count, embedding) VALUES (...)
   ```

**API calls made:** ceil(total_new_chunks / 100) embedding batch calls

**DB calls made:** 1 INSERT per chunk

**Output:** (missing_count, repaired_sources, total_chunks, skipped_no_text)

---

### Sync Summary — All API Calls for a Typical Run

For a typical sync with 757 articles (43 new):

| Step | External API Calls | DB Calls |
|------|-------------------|----------|
| Fetch articles | ~25-38 Readwise GET requests | 0 |
| Store + embed sources | 43 OpenRouter embedding calls | 757 SELECT + 43 INSERT = 800 |
| Chunk + embed chunks | ~3-5 OpenRouter batch embedding calls | ~350 chunk INSERTs |
| **Total** | **~70-85 API calls** | **~1,150 DB operations** |

---

## Flow 2: Chat (User Question → Answer with Sources)

Triggered by: User sends message in frontend → `POST /api/chat`

**File:** `chat/router.py` → `POST /api/chat`

### Step 1 — Hybrid Search (find relevant chunks)

**File:** `retrieval/search.py` → `hybrid_search(query, top_k=5)`

1. **Embed the query**:
   ```
   API call:  POST {embeddings_base_url}/embeddings
   Body:      { "model": "openai/text-embedding-3-small", "input": ["user's question"] }
   → 1536-dim vector
   ```

2. **Call hybrid_search SQL function** via Supabase RPC:
   ```
   DB call:  SELECT * FROM hybrid_search(
               query_embedding := [1536 floats],
               query_text := 'user question',
               match_count := 5,
               date_after := null,
               date_before := null
             )
   ```
   Inside the SQL function:
   - **Vector score**: `1 - (chunks.embedding <=> query_embedding)` — cosine similarity (0 to 1)
   - **FTS score**: `ts_rank(to_tsvector('english', chunks.content), plainto_tsquery('english', query_text))`
   - **Hybrid score**: `0.7 * vector_score + 0.3 * fts_score`
   - Returns top-K chunks joined with source metadata (title, author, url, published_at)

**Output:** List of `SearchResult` objects with scores and source info

---

### Step 2 — Cross-Session Memory

**File:** `chat/memory.py` → `retrieve_memory_context(query, conversation_id)`

1. **Embed the query** (separate embedding call):
   ```
   API call:  POST {embeddings_base_url}/embeddings
   Body:      { "model": "openai/text-embedding-3-small", "input": ["user's question"] }
   ```

2. **Search past assistant messages**:
   ```
   DB call:  SELECT * FROM search_past_messages(
               query_embedding := [1536 floats],
               exclude_conversation_id := '{current_conv_id}',
               match_count := 3
             )
   ```
   - Finds similar things the assistant said in OTHER conversations
   - Excludes current conversation to avoid self-reference

**Output:** Formatted string like `[PAST CONVERSATIONS]\n- Conversation 'title' (date): snippet`

---

### Step 3 — Build LLM Prompt

**File:** `chat/conversation.py` → `build_messages_for_llm(system_prompt, history, user_message, memory_context)`

1. **Get conversation history**:
   ```
   DB call:  SELECT * FROM messages WHERE conversation_id = '{id}' ORDER BY created_at
   ```

2. **Assemble messages array** for LLM:
   ```
   [
     { "role": "system", "content": system_prompt + memory_context },
     ...last 10 messages from history (capped to prevent context overflow)...,
     { "role": "user", "content": "SOURCES:\n[Source: Title]\nchunk_content\n...\n\nQUESTION:\nuser's question" }
   ]
   ```

The system prompt instructs the LLM to:
- Cite sources when answering
- Structure response as [FROM YOUR SOURCES] and [ANALYSIS] sections
- Be a personal knowledge assistant

---

### Step 4 — LLM Completion

```
API call:  POST {llm_base_url}/chat/completions
Body:      {
             "model": "meta-llama/llama-3.1-8b-instruct",
             "messages": [system, ...history, user_with_sources]
           }
→ response.choices[0].message.content
```

---

### Step 5 — Save Messages

1. **Save user message** (no embedding):
   ```
   DB call:  INSERT INTO messages (conversation_id, role, content) VALUES (...)
   DB call:  UPDATE conversations SET updated_at = now() WHERE id = '{id}'
   ```

2. **Save assistant message** (with embedding for future cross-session memory):
   ```
   API call:  POST {embeddings_base_url}/embeddings  (embed the assistant's response)
   DB call:   INSERT INTO messages (conversation_id, role, content, embedding) VALUES (...)
   DB call:   UPDATE conversations SET updated_at = now() WHERE id = '{id}'
   ```

---

### Chat Summary — All API Calls per Single Message

| Step | External API Calls | DB Calls |
|------|-------------------|----------|
| Hybrid search (embed query) | 1 OpenRouter embedding | 1 RPC (hybrid_search) |
| Memory retrieval (embed query) | 1 OpenRouter embedding | 1 RPC (search_past_messages) |
| Get history | 0 | 1 SELECT |
| LLM completion | 1 OpenRouter chat completion | 0 |
| Save user message | 0 | 2 (INSERT + UPDATE) |
| Save assistant message | 1 OpenRouter embedding | 2 (INSERT + UPDATE) |
| **Total per message** | **4 API calls** | **7 DB operations** |

---

## Flow 3: Topic Assignment (Phase 3 — Exists But Not Yet Run)

Triggered by: `second-brain assign-topics` CLI command

**File:** `ingestion/clustering.py` → `assign_topics_to_unassigned_sources(db, llm_provider, limit)`

For each unassigned source:

1. **Get source embedding** from `sources.source_embedding`
2. **Find best matching topic**:
   ```
   DB call:  SELECT * FROM match_topic(query_embedding, match_threshold=0.65, match_count=1)
   ```
3. **If match found** (similarity >= 0.65): assign source to existing topic
4. **If no match**: create new topic:
   - Call LLM to generate topic name (2-6 words)
   - Insert into `topics` table with centroid = source embedding
   - Insert into `source_topics` join table
   - Recompute topic centroid (mean of all member embeddings, normalized)

---

## Backend File Structure

```
backend/second_brain/
├── __init__.py
├── __main__.py          → python -m second_brain entry point
├── cli.py               → Typer CLI: sync, query, backfill-source-embeddings, assign-topics
├── config.py            → YAML + env var config loader → AppConfig singleton
├── db.py                → get_db_client() → supabase.Client
├── ingestion/
│   ├── readwise.py      → fetch_all_articles(), store_articles(), backfill_*()
│   ├── chunker.py       → chunk_text(), store_chunks_with_embeddings()
│   └── clustering.py    → assign_topics_to_unassigned_sources()
├── retrieval/
│   └── search.py        → hybrid_search() → list[SearchResult]
├── chat/
│   ├── router.py        → FastAPI endpoints: /api/chat, /api/conversations, /api/sync
│   ├── conversation.py  → CRUD: create/list conversations, get/save messages
│   └── memory.py        → retrieve_memory_context() for cross-session memory
└── providers/
    ├── embeddings.py    → EmbeddingProvider ABC → OpenRouterEmbeddingProvider
    └── llm.py           → LLMProvider ABC → OpenRouterLLMProvider
```

## Frontend File Structure

```
frontend/src/
├── app/
│   ├── page.tsx             → Root redirect to /chat
│   ├── layout.tsx           → Root layout with sidebar
│   └── chat/
│       ├── page.tsx         → New chat page
│       ├── NewChatClient.tsx → New chat UI (client component)
│       └── [id]/
│           ├── page.tsx     → Existing chat page (dynamic route)
│           └── ExistingChatClient.tsx → Existing chat UI
├── components/
│   ├── ChatPanel.tsx        → Message input + display area
│   ├── ConvSidebar.tsx      → Conversation list sidebar
│   ├── IngestionPanel.tsx   → Sync trigger UI
│   └── MessageBubble.tsx    → Individual message rendering
└── lib/
    ├── api.ts               → API client functions
    └── types.ts             → TypeScript types
```

### Frontend → Backend Communication
- Next.js proxy: all `/api/*` requests are proxied to `http://localhost:8000/api/*`
- Key API calls from `lib/api.ts`:
  - `GET /api/conversations` → list sidebar conversations
  - `POST /api/conversations` → create new conversation
  - `PATCH /api/conversations/{id}` → rename conversation
  - `GET /api/conversations/{id}/messages` → load message history
  - `POST /api/chat` → send message, get AI response with sources
  - `POST /api/sync` → trigger Readwise sync

---

## All Backend API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | Send message, get AI response + sources |
| POST | `/api/conversations` | Create new conversation |
| GET | `/api/conversations` | List conversations (limit 50) |
| GET | `/api/conversations/{id}/messages` | Get messages for conversation |
| PATCH | `/api/conversations/{id}` | Rename conversation |
| POST | `/api/sync` | Trigger Readwise sync from UI |

## All CLI Commands

| Command | Purpose |
|---------|---------|
| `second-brain sync [--limit N]` | Full Readwise sync: fetch → store → chunk → embed |
| `second-brain query "question" [--top-k N] [--after DATE] [--before DATE]` | Hybrid search from terminal |
| `second-brain backfill-source-embeddings [--limit N]` | Fill NULL source_embedding values |
| `second-brain assign-topics [--limit N]` | Assign sources to topic clusters |

---

## Key Dependencies

### Backend (pyproject.toml)
| Package | Purpose |
|---------|---------|
| fastapi + uvicorn | Web server |
| typer + rich | CLI framework |
| supabase | Database client |
| openai | OpenRouter API client (OpenAI-compatible SDK) |
| httpx | Readwise API HTTP client |
| tiktoken | Token counting for chunking |
| python-dotenv | Load .env file |
| pyyaml | Parse config.yaml |

### Frontend (package.json)
| Package | Purpose |
|---------|---------|
| next | React framework |
| react + react-dom | UI library |
| tailwindcss | Styling |

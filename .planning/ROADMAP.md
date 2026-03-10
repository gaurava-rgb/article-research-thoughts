# Roadmap: Second Brain — Personal Knowledge System

**Core Value:** The system must answer "what do I actually think about X?" by synthesizing across all saved sources — not just retrieve matching text chunks.

**Created:** 2026-03-10
**Granularity:** Standard (5-8 phases)
**Coverage:** 33/33 v1 requirements mapped

---

## Phases

- [x] **Phase 1: Foundation** - Schema, ingestion pipeline, and retrieval — user can sync Readwise corpus and query it via CLI (completed 2026-03-10)
- [x] **Phase 2: Chat UI + Memory** - Browser chat interface with conversation history — user can ask questions and continue past sessions (completed 2026-03-10)
- [ ] **Phase 3: Clustering + Topic Evolution** - Articles auto-organize into topics that update as new content arrives
- [ ] **Phase 4: Synthesis Engine** - Narrative answers across multiple sources with source attribution and contradiction detection
- [ ] **Phase 5: Proactive Insights + Digests** - System surfaces patterns, contradictions, and weekly summaries without being asked

---

## Phase Details

### Phase 1: Foundation
**Goal**: User can sync their entire Readwise corpus, have it stored with embeddings in Supabase, and query it via CLI to verify retrieval is working
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, ING-01, ING-02, ING-03, ING-04, ING-05, RET-01, RET-02, RET-03, RET-04
**Success Criteria** (what must be TRUE):
  1. Running the sync command imports all Readwise articles with no missing pages, and re-running it only processes new articles
  2. Each article's chunks are stored in Supabase with embeddings in pgvector — a CLI query returns semantically relevant results (not just keyword matches)
  3. Hybrid search (vector + keyword) returns results filtered by date range alongside source metadata (title, author, URL)
  4. LLM provider and embedding provider can be swapped by editing config.yaml without touching source code
  5. The full database schema (sources, chunks, topics, source_topics, conversations, messages, insights) is in schema.sql and applied in one command
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Database schema (all 7 tables) + Python project scaffold + config.yaml + provider abstraction
- [ ] 01-02-PLAN.md — Readwise sync CLI: paginated fetch, chunking, embedding generation, incremental sync
- [ ] 01-03-PLAN.md — Hybrid retrieval CLI: vector + FTS search, date filters, formatted result display

### Phase 2: Chat UI + Memory
**Goal**: User can open a browser, ask a question, have a multi-turn conversation, and return to that conversation in a future session
**Depends on**: Phase 1
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-07, CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. User can type a question in the chat UI and receive a formatted markdown response with source citation cards they can click to open the original article
  2. Follow-up questions in the same session understand prior context ("what else did those authors write about it?" resolves correctly)
  3. Past conversations appear in the sidebar — user can click one, see the full history, and continue asking questions
  4. The system recalls relevant past conversations when answering new questions ("we discussed this in a March session")
  5. Frontend is deployed to Vercel and accessible via URL; source ingestion panel allows triggering a Readwise sync from the UI
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — FastAPI chat backend: schema additions, conversation CRUD, memory retrieval, streaming /api/chat endpoint
- [ ] 02-02-PLAN.md — Next.js frontend scaffold: chat UI, message bubbles, citation cards (UI-02), section styling (UI-03), conversation sidebar (UI-04)
- [ ] 02-03-PLAN.md — Source ingestion panel: Readwise sync button + URL paste field (UI-05), POST /api/sync endpoint
- [ ] 02-04-PLAN.md — Vercel deployment: api/index.py entrypoint, vercel.json config, deploy to production (UI-07)

### Phase 3: Clustering + Topic Evolution
**Goal**: Articles automatically organize into coherent topic clusters on ingestion, and those clusters update as the corpus grows — no manual tagging required
**Depends on**: Phase 1
**Requirements**: STR-01, STR-02, STR-03
**Success Criteria** (what must be TRUE):
  1. After syncing new articles, each article is assigned to a topic cluster automatically — no user action required
  2. When a new article joins an existing topic, the topic summary is rewritten to reflect the expanded set of sources
  3. Temporal queries work: asking "what changed about X between Q3 and Q4?" returns an answer grounded in publication dates
**Plans**: TBD

### Phase 4: Synthesis Engine
**Goal**: User asks a complex question and receives a narrative answer that synthesizes across multiple sources, clearly attributed, with contradictions surfaced
**Depends on**: Phase 2, Phase 3
**Requirements**: SYN-01, SYN-02, SYN-03, SYN-04
**Success Criteria** (what must be TRUE):
  1. A question like "what do I think about AI safety?" returns a narrative synthesis across multiple articles — not a list of excerpts
  2. Every response has a clearly marked [FROM YOUR SOURCES] section and a [LLM ANALYSIS] section with distinct visual styling
  3. Every response cites specific articles with clickable links — user can trace each claim to its source
  4. When sources contradict each other on a topic, the response surfaces the contradiction explicitly ("Source A argues X while Source B argues Y")
**Plans**: TBD

### Phase 5: Proactive Insights + Digests
**Goal**: The system works in the background to detect patterns and contradictions across the corpus and delivers weekly summaries without the user asking
**Depends on**: Phase 3, Phase 4
**Requirements**: WORK-01, WORK-02, WORK-03, UI-06
**Success Criteria** (what must be TRUE):
  1. A weekly digest is generated summarizing new articles ingested that week, which topics they joined, and what themes are emerging
  2. The system stores detected patterns and contradictions as insights — these accumulate automatically as new articles are ingested
  3. The chat UI shows an unseen insight count badge ("3 new insights") and the user can open and read each insight
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete   | 2026-03-10 |
| 2. Chat UI + Memory | 4/4 | Complete   | 2026-03-10 |
| 3. Clustering + Topic Evolution | 0/? | Not started | - |
| 4. Synthesis Engine | 0/? | Not started | - |
| 5. Proactive Insights + Digests | 0/? | Not started | - |

---

## Coverage Map

| Requirement | Phase |
|-------------|-------|
| INFRA-01 | Phase 1 |
| INFRA-02 | Phase 1 |
| INFRA-03 | Phase 1 |
| ING-01 | Phase 1 |
| ING-02 | Phase 1 |
| ING-03 | Phase 1 |
| ING-04 | Phase 1 |
| ING-05 | Phase 1 |
| RET-01 | Phase 1 |
| RET-02 | Phase 1 |
| RET-03 | Phase 1 |
| RET-04 | Phase 1 |
| UI-01 | Phase 2 |
| UI-02 | Phase 2 |
| UI-03 | Phase 2 |
| UI-04 | Phase 2 |
| UI-05 | Phase 2 |
| UI-07 | Phase 2 |
| CHAT-01 | Phase 2 |
| CHAT-02 | Phase 2 |
| CHAT-03 | Phase 2 |
| CHAT-04 | Phase 2 |
| STR-01 | Phase 3 |
| STR-02 | Phase 3 |
| STR-03 | Phase 3 |
| SYN-01 | Phase 4 |
| SYN-02 | Phase 4 |
| SYN-03 | Phase 4 |
| SYN-04 | Phase 4 |
| WORK-01 | Phase 5 |
| WORK-02 | Phase 5 |
| WORK-03 | Phase 5 |
| UI-06 | Phase 5 |

**Total: 33/33 v1 requirements mapped**

---
*Roadmap created: 2026-03-10*
*Phase 1 plans created: 2026-03-10*
*Phase 2 plans created: 2026-03-10*

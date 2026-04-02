---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 5
current_plan: complete
status: complete
stopped_at: All 5 phases complete. 35/35 backend tests passing. TypeScript clean. Ready for deployment or post-v1 work.
last_updated: "2026-04-02T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 11
  completed_plans: 11
---

# State: Second Brain — Personal Knowledge System

**Project:** Second Brain — Personal Knowledge System
**Core Value:** Answer "what do I actually think about X?" by synthesizing across all saved sources
**Last Updated:** 2026-03-11

---

## Current Position

**Milestone:** 1 (of 1 planned)
**Current Phase:** 5 (complete)
**Current Plan:** All plans complete
**Status:** Complete

```
Progress: 11 of 11 plans complete
[██████████] 100%
```

---

## Phase Status

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Foundation | Complete (3/3 plans done) | 3 |
| 2 | Chat UI + Memory | Complete (4/4 plans done; Vercel deploy checkpoint pending human action) | 4 |
| 3 | Clustering + Topic Evolution | Complete — 764 sources → 354 topics, /api/topics live, sync wired | 4 |
| 4 | Synthesis Engine | Complete — narrative synthesis, [FROM YOUR SOURCES]/[ANALYSIS]/[CONTRADICTIONS] sections, top_k=30 dedup | TBD |
| 5 | Proactive Insights + Digests | Complete — weekly digest, insights table, UI badge + panel, related-convs nudge, memory arch fix | TBD |

---

## Performance Metrics

- Plans executed: 11
- Plans passing on first run: 11/11 (100%)
- Phases completed: 5/5
- Requirements mapped: 33/33
- Backend tests: 35/35 passing
- TypeScript: clean (0 errors)

---

## Accumulated Context

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Python FastAPI backend | Decided; not up for reconsideration |
| Supabase + pgvector | User already has Supabase; vectors + relational in one place |
| OpenRouter for LLM + embeddings | Single API to swap between Claude, GPT-4o, Gemini |
| Claude Sonnet as default | Strong synthesis reasoning |
| config.yaml for provider abstraction | LLM and embedding provider must be swappable without code changes |
| Full schema from day one | schema.sql covers all tables; avoids migrations across phases |
| Next.js frontend to Vercel | Deployment target decided |
| All 7 tables in schema.sql upfront | Avoids ALTER TABLE migrations across phases |
| Provider abstraction via ABC + factory | Callers never change when provider switches |
| Config env var resolution at load time | _env fields resolved to values at startup |
| pageCursor pagination | Prevents missing articles when Readwise corpus shifts between pages |
| Sentence-aware chunking before token accumulation | Avoids mid-sentence cuts; better embedding quality |
| Lazy imports in CLI sync command | Keeps --help instantaneous; heavy imports only when sync actually runs |
| Hybrid score = 70% vector + 30% FTS | Vector-heavy because semantic meaning is the primary retrieval signal in a personal knowledge base; weights documented in schema.sql and tunable |
| Lazy imports in retrieval/search.py | config.py validates env vars at import time; deferring imports inside hybrid_search() consistent with established lazy-import pattern |
| Module-level import of get_db_client for test patchability | db.py only loads supabase library (no env vars triggered); allows patch("second_brain.chat.conversation.get_db_client") in tests |
| Lazy wrapper function for get_embedding_provider in memory.py | embeddings.py imports cfg at module level (triggers env var validation); wrapper defers the real import to call time while still being patchable by name |
| SSE format: token events + sources event + [DONE] terminator | Standard SSE pattern for streaming LLM responses with source attribution |
| Async params pattern for Next.js 15+ dynamic routes | params typed as Promise<{id}> and awaited in async server component — required for Next.js 15+/16 |
| MemoizedMarkdown wraps react-markdown in React.memo | Prevents re-render thrash during SSE token streaming — each token update would re-render the whole markdown tree without memoization |
| Sync runs to completion before returning to UI | Thread executor approach gives user real success/error feedback — fire-and-forget would show no result |
| URL ingestion field is UI-only placeholder in Phase 2 | Backend URL ingestion pipeline deferred to Phase 3; UI element satisfies UI-05 spec at front-end level |
| fastapi and uvicorn added to pyproject.toml | Were missing despite router.py requiring them; added as Rule 3 auto-fix |
| api/index.py at repo root is Vercel Python entrypoint | Vercel requires this exact path for the Python serverless function |
| maxDuration: 300 in vercel.json | Hobby plan maximum; needed for Readwise sync (60-120s) and LLM streaming |
| Whole-source vectors stored on `sources.source_embedding` during ingestion | Phase 3 should reuse the current schema/flow instead of following older `sources.embedding` plan wording |

### Known Constraints

- READWISE_TOKEN available in shell environment
- Prior pagination bug in Readwise API loop — ingestion must handle pagination robustly
- User is a learning coder — code must be clean, well-commented, incremental
- Token budget: $20/month Claude plan — minimize unnecessary agent spawns

### Technical Notes

- Database tables needed: sources, chunks, topics, source_topics, conversations, messages, insights
- Hybrid search = pgvector similarity + PostgreSQL full-text search
- Incremental sync: track last_ingested_at or use Readwise cursor to skip already-processed articles
- Phase 3 depends on Phase 1 (needs corpus); Phase 4 depends on Phase 2 + Phase 3; Phase 5 depends on Phase 3 + Phase 4

### Open Questions

- Backend deployment target: local dev server vs. cloud (Railway, Render, Fly.io)?
- Weekly digest delivery mechanism: stored in DB and viewed in UI, or email, or both?
- Do older rows with NULL `sources.source_embedding` need a backfill before Phase 3 clustering is enabled broadly?

### Blockers

None currently.

---

## Session Continuity

**Last session:** 2026-04-02

**Stopped at:** All 5 phases complete. v1 milestone done.

**Next action options (post-v1):**
- Vercel deployment — still pending human action (set env vars, `vercel --yes`, verify live URL)
- Pattern/contradiction insight generation — `generate_digest` is built; pattern detection across all topics would extend WORK-02
- Corpus completeness — 765 sources, all chunked; consider scheduled auto-sync
- Supabase storage — was near free-tier limit (500MB) post-dedup; monitor

**Open questions carried forward:**
- Backend deployment target: local dev only, or cloud (Railway/Render/Fly.io)?
- Weekly digest delivery: UI only (current), or email too?

---
*State initialized: 2026-03-10 after roadmap creation*

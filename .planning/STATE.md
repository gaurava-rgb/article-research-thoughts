# State: Second Brain — Personal Knowledge System

**Project:** Second Brain — Personal Knowledge System
**Core Value:** Answer "what do I actually think about X?" by synthesizing across all saved sources
**Last Updated:** 2026-03-10

---

## Current Position

**Milestone:** 1 (of 1 planned)
**Current Phase:** 1 — Foundation
**Current Plan:** None (planning not yet started)
**Status:** Ready to plan

```
Progress: Phase 1 of 5
[          ] 0% complete
```

---

## Phase Status

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Foundation | Not started | TBD |
| 2 | Chat UI + Memory | Not started | TBD |
| 3 | Clustering + Topic Evolution | Not started | TBD |
| 4 | Synthesis Engine | Not started | TBD |
| 5 | Proactive Insights + Digests | Not started | TBD |

---

## Performance Metrics

- Plans executed: 0
- Plans passing on first run: —
- Phases completed: 0/5
- Requirements mapped: 33/33

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
- Clustering algorithm: k-means, HDBSCAN, or LLM-based topic assignment?

### Blockers

None currently.

---

## Session Continuity

**To resume:** Run `/gsd:plan-phase 1` to begin planning Phase 1 (Foundation).

**Next action:** Plan Phase 1 — schema.sql, ingestion pipeline, hybrid retrieval, provider config.

---
*State initialized: 2026-03-10 after roadmap creation*

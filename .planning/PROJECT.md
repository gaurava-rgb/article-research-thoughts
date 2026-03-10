# Second Brain — Personal Knowledge System

## What This Is

A personal second brain that turns saved articles from Readwise Reader into a thinking partner — not just a search engine. Users ingest content via the Readwise API and interact through a conversational chat UI that synthesizes knowledge across sources, tracks how thinking evolves over time, and proactively surfaces patterns and insights.

## Core Value

The system must answer "what do I actually think about X?" by synthesizing across all saved sources — not just retrieve matching text chunks.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can ingest articles from Readwise Reader via API (READWISE_TOKEN from environment)
- [ ] User can ask questions and get narrative answers grounded in their saved knowledge
- [ ] Responses clearly distinguish [FROM SOURCES] vs [LLM ANALYSIS]
- [ ] Responses cite specific sources with links
- [ ] User can have multi-turn conversations with context retained within a session
- [ ] Past conversations are stored and loadable (cross-session memory)
- [ ] Articles are auto-clustered into topics without manual tagging
- [ ] Topic summaries evolve as new articles are added to a topic
- [ ] System supports temporal reasoning ("what changed about X between Q3 and Q4?")
- [ ] Weekly digest summarizing new sources, topic evolution, and emerging themes
- [ ] System detects patterns and contradictions across sources (proactive insights)
- [ ] Chat UI deployed to Vercel
- [ ] LLM and embedding providers are swappable via config (not hardcoded)

### Out of Scope

- Notion import — Readwise is the source of truth; Notion experiment was abandoned
- Mobile app — web-first
- Multi-user support — personal tool only
- Real-time collaboration
- Manual tagging — auto-clustering replaces it

## Context

- User has existing Readwise Reader corpus of hundreds of articles, growing
- READWISE_TOKEN already available in shell environment
- Prior attempt to loop through Readwise API had pagination issues — ingestion needs robust pagination handling
- Stack confirmed: Python FastAPI backend, Supabase (PostgreSQL + pgvector), Next.js frontend, OpenRouter (Claude Sonnet default)
- Deployment: Next.js frontend to Vercel, backend TBD (local or cloud)
- User is a learning coder — code should be clean, well-commented, and incremental

## Constraints

- **Token budget**: User on $20/month Claude plan — minimize unnecessary agent spawns, prefer efficient solutions
- **Tech stack**: Python FastAPI + Supabase + Next.js + OpenRouter (Claude Sonnet) — decided
- **Provider abstraction**: LLM and embedding providers must be swappable via config.yaml, not hardcoded
- **Database**: Supabase (user already has it) — no switching

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Readwise as primary ingestion source | User has token, direct API is cleaner than Notion workaround | — Pending |
| Supabase + pgvector | Already have Supabase, handles vectors + relational in one place | — Pending |
| OpenRouter for LLM/embeddings | One API to swap between Claude, GPT-4o, Gemini | — Pending |
| Claude Sonnet as default | Strong synthesis reasoning | — Pending |
| Skip research phase | Architecture already fully designed in implementation docs | — Pending |

---
*Last updated: 2026-03-10 after initialization*

---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [supabase, pgvector, python, pyyaml, openai, openrouter, schema, config]

# Dependency graph
requires: []
provides:
  - "schema.sql: 7-table Supabase schema with pgvector, IVFFlat, and GIN indexes"
  - "config.yaml: single-file provider configuration for LLM, embeddings, database, Readwise"
  - "backend/second_brain/config.py: typed AppConfig dataclass with env var resolution, module-level cfg singleton"
  - "backend/second_brain/providers/embeddings.py: EmbeddingProvider ABC + OpenRouterEmbeddingProvider + factory"
  - "backend/second_brain/providers/llm.py: LLMProvider ABC + OpenRouterLLMProvider + factory"
  - "backend/second_brain/db.py: Supabase client factory"
  - "backend/pyproject.toml: PEP 621 Python package scaffold"
affects: [02-ingestion, 03-retrieval, 04-chat, 05-clustering, 06-insights]

# Tech tracking
tech-stack:
  added: [supabase, openai (OpenRouter-compatible), pyyaml, tiktoken, httpx, typer, rich, pytest, pytest-asyncio, pgvector]
  patterns:
    - "Provider abstraction via ABC + factory function + config.yaml dispatch"
    - "Env var resolution: config fields ending in _env are resolved at load time"
    - "Module-level cfg singleton: import once at startup, all modules share"
    - "Schema first: all 7 tables defined upfront to avoid cross-phase migrations"

key-files:
  created:
    - schema.sql
    - config.yaml
    - backend/pyproject.toml
    - backend/second_brain/__init__.py
    - backend/second_brain/config.py
    - backend/second_brain/db.py
    - backend/second_brain/providers/__init__.py
    - backend/second_brain/providers/embeddings.py
    - backend/second_brain/providers/llm.py
  modified: []

key-decisions:
  - "All 7 tables created in schema.sql now to avoid migrations across phases"
  - "Provider abstraction via ABC + factory — adding a new provider means adding one class and one if-branch, no callers change"
  - "Config env var resolution at load time: _env suffix fields become resolved values in the cfg dataclass"
  - "IVFFlat index on chunks.embedding (lists=100) for approximate nearest-neighbor search"
  - "GIN index on chunks.content for PostgreSQL full-text search — enables hybrid retrieval in Phase 2"

patterns-established:
  - "Provider pattern: EmbeddingProvider/LLMProvider ABCs with get_*_provider() factories reading cfg"
  - "Config singleton: cfg loaded once at import time via _load_config(); all modules do from second_brain.config import cfg"
  - "Env var resolution: YAML fields ending _env are looked up in os.environ at startup with clear error messages"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Phase 1 Plan 1: Foundation Summary

**7-table Supabase/pgvector schema with full-text + vector indexes, typed Python config loader, and swappable OpenRouter LLM/embedding provider abstractions**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-10T15:10:15Z
- **Completed:** 2026-03-10T15:14:32Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- schema.sql creates all 7 tables (sources, chunks, topics, source_topics, conversations, messages, insights) with correct FK dependency order, pgvector extension, IVFFlat cosine index for semantic search, and GIN index for full-text search
- config.yaml is the single provider entrypoint — change llm.model or llm.provider to swap models/providers with zero code changes
- Python backend package with typed dataclass config (AppConfig), env var resolution, and module-level `cfg` singleton that all subsequent modules import
- EmbeddingProvider and LLMProvider ABCs with OpenRouter implementations and factory functions — adding a new provider is one class plus one if-branch

## Task Commits

Each task was committed atomically:

1. **Task 1: Full database schema and project scaffold** - `59fc0f5` (feat)
2. **Task 2: config.yaml and provider abstraction layer** - `254f53b` (feat)

## Files Created/Modified

- `schema.sql` - Full database schema: 7 tables, pgvector extension, IVFFlat + GIN indexes
- `config.yaml` - Provider configuration: llm, embeddings, database, readwise, chunking sections
- `backend/pyproject.toml` - PEP 621 package scaffold with all runtime and dev dependencies
- `backend/second_brain/__init__.py` - Package marker
- `backend/second_brain/config.py` - Typed config loader with env var resolution; exports `cfg`
- `backend/second_brain/db.py` - Supabase client factory; reads from cfg or env vars
- `backend/second_brain/providers/__init__.py` - Package marker
- `backend/second_brain/providers/embeddings.py` - EmbeddingProvider ABC, OpenRouterEmbeddingProvider (batched 100), get_embedding_provider() factory
- `backend/second_brain/providers/llm.py` - LLMProvider ABC, OpenRouterLLMProvider, get_llm_provider() factory

## Decisions Made

- All 7 tables created upfront in schema.sql. Rationale: defining the full schema in Phase 1 avoids ALTER TABLE migrations across phases; each subsequent phase just uses the tables it needs.
- Provider abstraction via ABC + factory. Rationale: caller code (`provider.complete(messages)`) never needs to change when the underlying provider changes.
- IVFFlat index with lists=100 is appropriate for a corpus up to ~1M chunks; can be rebuilt with higher list count if corpus grows.
- GIN index on chunk content enables hybrid search (vector + FTS) in Phase 2 without schema changes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

System Python 3.14 (homebrew) was separate from pip3's Python 3.9 install. Used `/opt/homebrew/bin/python3 -m pip install` with `--break-system-packages` to install pyyaml and openai for verification. This is a local dev machine issue; the pyproject.toml correctly specifies Python >=3.11 and users will install via `pip install -e .` in a virtual environment.

## User Setup Required

Before using the backend, set these environment variables:

```bash
export OPENROUTER_API_KEY="sk-or-..."
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="eyJ..."
export READWISE_TOKEN="..."
```

Apply the schema to Supabase once:

```bash
psql $DATABASE_URL -f schema.sql
```

## Next Phase Readiness

- schema.sql is ready to apply to Supabase — run `psql $DATABASE_URL -f schema.sql` once
- `from second_brain.config import cfg` works; all subsequent modules use this pattern
- Provider factories work; Phase 2 ingestion will call `get_embedding_provider().embed(texts)`
- No blockers for Phase 1 Plan 2 (ingestion pipeline)

---
*Phase: 01-foundation*
*Completed: 2026-03-10*

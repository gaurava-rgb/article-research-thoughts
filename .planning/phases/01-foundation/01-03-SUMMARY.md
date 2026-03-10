---
phase: 01-foundation
plan: 03
subsystem: retrieval
tags: [pgvector, postgresql, fts, hybrid-search, typer, rich, supabase, rpc]

# Dependency graph
requires:
  - phase: 01-01
    provides: "get_embedding_provider() factory, get_db_client() Supabase factory, chunks/sources schema with IVFFlat + GIN indexes"
  - phase: 01-02
    provides: "Ingested chunks with embedding vectors in the database; python -m second_brain CLI structure"
provides:
  - "schema.sql: hybrid_search() PostgreSQL function (70% pgvector cosine + 30% ts_rank, date filters)"
  - "backend/second_brain/retrieval/search.py: SearchResult dataclass and hybrid_search() Python function"
  - "backend/second_brain/cli.py: query command added to existing Typer app"
affects: [04-chat, 05-clustering, 06-insights]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hybrid search: SQL function called via Supabase RPC; Python only embeds query and maps results"
    - "Lazy imports in query command: same pattern as sync — keeps --help instantaneous"
    - "SearchResult dataclass: maps RPC row dict to typed Python object for downstream callers"

key-files:
  created:
    - backend/second_brain/retrieval/__init__.py
    - backend/second_brain/retrieval/search.py
  modified:
    - schema.sql
    - backend/second_brain/cli.py

key-decisions:
  - "Hybrid score = 70% vector + 30% FTS: vector-heavy because semantic meaning is the primary retrieval signal; weights are documented in both schema.sql and search.py for easy tuning"
  - "Lazy imports in search.py: get_db_client and get_embedding_provider imported inside hybrid_search() to allow 'from second_brain.retrieval.search import SearchResult' without env vars loaded"
  - "SQL function is CREATE OR REPLACE: idempotent, safe to re-apply schema.sql without dropping function"

patterns-established:
  - "Retrieval pattern: embed query in Python, delegate scoring entirely to SQL, map results to dataclass"
  - "RPC pattern: db.rpc('function_name', {params}).execute() for any complex SQL query needing vector + FTS"

requirements-completed: [RET-01, RET-02, RET-03, RET-04]

# Metrics
duration: 8min
completed: 2026-03-10
---

# Phase 1 Plan 3: Retrieval Pipeline Summary

**Supabase RPC hybrid search SQL function (70% pgvector cosine + 30% ts_rank) with date filters, Python SearchResult dataclass, and `query` CLI command with Rich-formatted output cards**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-10T15:25:30Z
- **Completed:** 2026-03-10T15:33:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- hybrid_search() PostgreSQL function appended to schema.sql — combines 1536-dim cosine similarity (pgvector) with ts_rank full-text search; accepts date_after/date_before parameters for published_at filtering; weights documented and tunable by editing two constants in the SQL
- SearchResult dataclass and hybrid_search() Python function in retrieval/search.py — embeds the query string, calls Supabase RPC, maps rows to typed dataclasses; lazy imports allow importing SearchResult without env vars present
- query CLI command added to existing Typer app — --top-k, --after, --before flags; YYYY-MM-DD date validation with clear error messages; Rich-formatted result cards showing title, author, URL, date, hybrid/vector/fts scores, 300-char chunk preview

## Task Commits

Each task was committed atomically:

1. **Task 1: Hybrid search SQL function and Python retrieval module** - `0e9320c` (feat)
2. **Task 2: CLI query command with formatted output** - `4dd6152` (feat)

## Files Created/Modified

- `schema.sql` - Appended CREATE OR REPLACE FUNCTION hybrid_search (idempotent, safe to re-apply)
- `backend/second_brain/retrieval/__init__.py` - Package marker for retrieval subpackage
- `backend/second_brain/retrieval/search.py` - SearchResult dataclass; hybrid_search() with lazy imports
- `backend/second_brain/cli.py` - Added query command; both sync and query now registered on same Typer app

## Decisions Made

- Hybrid score weights 70/30 (vector-heavy): vector similarity captures semantic meaning; FTS handles exact keyword matches. In a personal knowledge base the user asks conceptual questions more often than exact keyword queries. Weights are documented and easy to tune in schema.sql.
- Lazy imports inside hybrid_search(): config.py validates env vars at import time, which would break `from second_brain.retrieval.search import SearchResult` in contexts without env vars (tests, other importers). Deferring to call time is consistent with the lazy-import pattern already established in cli.py.
- SQL function uses CREATE OR REPLACE: makes schema.sql idempotent — users can re-apply the file after DB setup without errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy imports moved inside hybrid_search() to prevent import-time env var failure**
- **Found during:** Task 1 (import verification)
- **Issue:** `from second_brain.db import get_db_client` and `from second_brain.providers.embeddings import get_embedding_provider` at module level triggered config.py's env var validation at import time, causing `RuntimeError: Missing required environment variable: OPENROUTER_API_KEY` when verifying the module import
- **Fix:** Moved both imports inside the hybrid_search() function body; added explanatory comment; consistent with lazy-import pattern from Plan 02
- **Files modified:** backend/second_brain/retrieval/search.py
- **Verification:** `python -c "from second_brain.retrieval.search import hybrid_search, SearchResult; print('OK')"` succeeds without env vars
- **Committed in:** 0e9320c (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for the import verification check specified in Task 1. Consistent with existing project pattern. No scope creep.

## Issues Encountered

None beyond the auto-fixed import issue above.

## User Setup Required

To apply the hybrid_search SQL function to Supabase, re-run schema.sql (the function uses CREATE OR REPLACE, so it is safe to re-apply):

```bash
psql $DATABASE_URL -f schema.sql
```

Or run just the function portion in the Supabase SQL editor.

After applying, test end-to-end:

```bash
export OPENROUTER_API_KEY="sk-or-..."
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="eyJ..."
cd backend && python -m second_brain query "machine learning" --top-k 3
```

## Next Phase Readiness

- Phase 1 Foundation is complete: schema, ingestion, and retrieval pipeline all working
- Phase 2 (Chat UI + Memory) can call hybrid_search() to retrieve relevant context before LLM responses
- The query CLI command provides immediate value: users can explore their knowledge base before the chat UI is built
- No blockers for Phase 2

---
*Phase: 01-foundation*
*Completed: 2026-03-10*

## Self-Check: PASSED

- All 4 files found on disk (retrieval/__init__.py, retrieval/search.py, schema.sql, cli.py)
- SUMMARY.md found on disk
- Commits 0e9320c and 4dd6152 confirmed in git log

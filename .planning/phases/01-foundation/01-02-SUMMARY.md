---
phase: 01-foundation
plan: 02
subsystem: ingestion
tags: [readwise, httpx, tiktoken, typer, rich, pgvector, chunking, embeddings, cli, supabase]

# Dependency graph
requires:
  - phase: 01-01
    provides: "cfg singleton, EmbeddingProvider ABC + get_embedding_provider() factory, get_db_client() Supabase factory"
provides:
  - "backend/second_brain/ingestion/readwise.py: ReadwiseArticle dataclass, fetch_all_articles() paginated API client, store_articles() upsert with readwise_id deduplication"
  - "backend/second_brain/ingestion/chunker.py: Chunk dataclass, chunk_text() sentence-aware ~500-token chunker with overlap, store_chunks_with_embeddings() batched embedding pipeline"
  - "backend/second_brain/cli.py: Typer sync command with --limit flag, rich progress output"
  - "backend/second_brain/__main__.py: enables python -m second_brain sync"
affects: [03-retrieval, 04-chat, 05-clustering, 06-insights]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deduplication by readwise_id: check before insert, return (new_count, skipped_count)"
    - "Sentence-aware chunking: split on '. ', '! ', '? ', '\\n\\n' to avoid mid-sentence cuts"
    - "pageCursor pagination: stable opaque token from Readwise API, loop until nextPageCursor is null"
    - "Lazy import pattern in CLI: heavy imports inside command function to keep --help fast"
    - "Overlap seed: last overlap_tokens tokens of previous chunk prepended to next for context continuity"

key-files:
  created:
    - backend/second_brain/ingestion/__init__.py
    - backend/second_brain/ingestion/readwise.py
    - backend/second_brain/ingestion/chunker.py
    - backend/second_brain/cli.py
    - backend/second_brain/__main__.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "pageCursor pagination (not offset-based): stable token prevents missing articles when corpus shifts"
  - "Deduplicate by readwise_id using SELECT before INSERT: simple and readable over upsert ON CONFLICT"
  - "chunk_text uses sentence splitting heuristic before accumulation: avoids mid-sentence cuts for better embedding quality"
  - "Lazy imports in sync command: keeps --help instantaneous, config only loaded when sync actually runs"
  - "Added __main__.py: enables python -m second_brain without installing the package"

patterns-established:
  - "Ingestion pattern: fetch -> deduplicate -> chunk -> embed -> store, each step a separate function"
  - "CLI structure: one Typer app in cli.py, commands import heavy modules lazily inside the function body"

requirements-completed: [ING-01, ING-02, ING-03, ING-04, ING-05]

# Metrics
duration: 12min
completed: 2026-03-10
---

# Phase 1 Plan 2: Readwise Ingestion Pipeline Summary

**Paginated Readwise Reader API client with readwise_id deduplication, tiktoken-based sentence-aware chunker with 50-token overlap, batched OpenRouter embedding pipeline, and Typer sync CLI with --limit flag**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-10T15:18:18Z
- **Completed:** 2026-03-10T15:30:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- fetch_all_articles() uses pageCursor pagination correctly (fixing the known prior bug of offset-based pagination missing articles); loops until nextPageCursor is null; filters articles with <50 chars of text
- store_articles() checks readwise_id existence before each insert — re-running sync is safe and skips already-ingested articles; returns (new_count, skipped_count) for progress reporting
- chunk_text() splits on sentence boundaries before accumulating, preventing mid-sentence cuts that hurt embedding quality; each new chunk is seeded with the last 50 tokens of the previous chunk for context continuity
- store_chunks_with_embeddings() batches embedding API calls at 100 texts/request matching the OpenRouterEmbeddingProvider.BATCH_SIZE
- sync CLI: fetch -> store -> chunk -> embed pipeline with rich-styled per-article progress output; --limit flag allows cheap testing without processing the full corpus

## Task Commits

Each task was committed atomically:

1. **Task 1: Readwise API client with pagination and DB storage** - `eba6161` (feat)
2. **Task 2: Text chunker, embedding pipeline, and sync CLI command** - `05dd5d4` (feat)

## Files Created/Modified

- `backend/second_brain/ingestion/__init__.py` - Package marker for ingestion subpackage
- `backend/second_brain/ingestion/readwise.py` - ReadwiseArticle dataclass; fetch_all_articles() paginated client; store_articles() deduplication upsert
- `backend/second_brain/ingestion/chunker.py` - Chunk dataclass; chunk_text() sentence-aware tiktoken chunker; store_chunks_with_embeddings() batched embedding pipeline
- `backend/second_brain/cli.py` - Typer app with sync command; rich progress output; lazy imports for fast --help
- `backend/second_brain/__main__.py` - Enables `python -m second_brain sync` without package install
- `backend/pyproject.toml` - Added `[project.scripts]` entry: `second-brain = "second_brain.cli:app"`

## Decisions Made

- pageCursor pagination over offset-based: Readwise's pageCursor is a stable opaque token. Offset-based pagination misses articles when the list shifts between pages (the documented prior bug). pageCursor is the correct approach.
- SELECT before INSERT for deduplication: simpler and more readable than ON CONFLICT upsert for this learning codebase. Performance is acceptable since sync runs periodically, not in tight loops.
- Sentence-aware splitting before accumulation: splitting on `. `, `! `, `? `, `\n\n` means chunk boundaries fall at natural sentence ends rather than mid-word, producing better embedding representations.
- Lazy imports inside sync(): avoids loading supabase, openai, tiktoken (slow imports) when the user runs `second-brain --help`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added __main__.py to enable python -m second_brain**
- **Found during:** Task 2 (CLI verification)
- **Issue:** Plan specifies `python -m second_brain sync` should work, but Python module invocation requires `__main__.py` in the package directory
- **Fix:** Created `backend/second_brain/__main__.py` that imports and calls `app()`
- **Files modified:** backend/second_brain/__main__.py
- **Verification:** `python -m second_brain --help` shows sync command
- **Committed in:** 05dd5d4 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for the `python -m second_brain sync` invocation specified in the plan. No scope creep.

## Issues Encountered

System Python 3.14 (homebrew) and pip3's Python 3.9 mismatch — same issue as Plan 01. Used `/opt/homebrew/bin/python3 -m pip install supabase --break-system-packages` to install for 3.14. The pyproject.toml already lists all dependencies correctly; this only affects the local dev verification environment, not production installs.

## User Setup Required

None — the required environment variables (READWISE_TOKEN, SUPABASE_URL, SUPABASE_KEY, OPENROUTER_API_KEY) were already documented in Plan 01's USER SETUP section.

To run a test sync:
```bash
export READWISE_TOKEN="..."
export SUPABASE_URL="..."
export SUPABASE_KEY="..."
export OPENROUTER_API_KEY="..."
cd backend && python -m second_brain sync --limit 3
```

## Next Phase Readiness

- sources table will be populated after first `sync` run
- chunks table with embedding vectors ready for pgvector similarity queries
- Plan 03 (retrieval) can call `get_embedding_provider().embed([query])` then query chunks.embedding using Supabase's pgvector RPC
- No blockers for Plan 01-03 (retrieval pipeline)

---
*Phase: 01-foundation*
*Completed: 2026-03-10*

## Self-Check: PASSED

- All 6 files found on disk
- Commits eba6161 and 05dd5d4 confirmed in git log

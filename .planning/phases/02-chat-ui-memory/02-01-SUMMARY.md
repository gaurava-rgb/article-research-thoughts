---
phase: 02-chat-ui-memory
plan: 01
subsystem: api
tags: [fastapi, supabase, pgvector, openai, sse, pytest, asyncio]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "get_db_client(), get_embedding_provider(), hybrid_search(), cfg — all consumed by chat router and memory module"

provides:
  - "FastAPI APIRouter with 5 chat/conversation endpoints (POST /chat SSE, POST /conversations, GET /conversations, GET /conversations/{id}/messages, PATCH /conversations/{id})"
  - "second_brain.chat.conversation: build_messages_for_llm, list_conversations, get_messages, save_message, save_message_with_embedding"
  - "second_brain.chat.memory: retrieve_memory_context — semantic search over past assistant messages"
  - "schema.sql Phase 2 additions: messages.embedding column, IVFFlat index, search_past_messages() SQL function"
  - "pytest test scaffold: pytest.ini (asyncio_mode=auto), tests/chat/ with test_conversation.py, test_memory.py, test_router.py"

affects: [02-02, 02-03, 02-04, frontend]

# Tech tracking
tech-stack:
  added: [pytest, pytest-asyncio, fastapi, httpx]
  patterns: ["Module-level import with lazy-wrapper pattern for patchable-but-deferred dependencies", "SSE streaming via FastAPI StreamingResponse with text/event-stream", "Fire-and-forget background embedding via asyncio.create_task + asyncio.to_thread"]

key-files:
  created:
    - backend/second_brain/chat/__init__.py
    - backend/second_brain/chat/conversation.py
    - backend/second_brain/chat/memory.py
    - backend/second_brain/chat/router.py
    - backend/tests/__init__.py
    - backend/tests/chat/__init__.py
    - backend/tests/chat/test_conversation.py
    - backend/tests/chat/test_memory.py
    - backend/tests/chat/test_router.py
    - backend/pytest.ini
  modified:
    - schema.sql

key-decisions:
  - "Module-level import of get_db_client in conversation.py and memory.py so tests can patch via 'second_brain.chat.conversation.get_db_client' — db.py only imports supabase library (no env vars triggered)"
  - "Lazy wrapper function for get_embedding_provider in memory.py — embeddings.py imports cfg at module level which triggers env var validation; wrapper defers until call time while still being patchable"
  - "History capped at last 10 messages in build_messages_for_llm to prevent context window overflow (per research doc pitfall 6)"
  - "Assistant messages saved with embedding via fire-and-forget background task to avoid blocking the SSE stream"

patterns-established:
  - "Patchable lazy import: use module-level wrapper function instead of bare lazy import when test patching is needed"
  - "SSE format: token events + sources event + [DONE] terminator"
  - "Cross-session memory: search_past_messages RPC injects relevant prior conversations into system prompt"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, UI-01]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 2 Plan 01: Chat Backend Summary

**FastAPI chat backend with SSE streaming, multi-turn conversation history, cross-session semantic memory via pgvector, and pytest test scaffold with asyncio support**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T19:59:48Z
- **Completed:** 2026-03-10T20:03:21Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Delivered 5 FastAPI chat endpoints: POST /chat (SSE stream), POST/GET /conversations, GET /conversations/{id}/messages, PATCH /conversations/{id}
- Built cross-session semantic memory (retrieve_memory_context) using search_past_messages() SQL function over pgvector message embeddings
- Created full pytest scaffold with asyncio_mode=auto and 5 passing unit tests covering CHAT-01 through CHAT-04

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test scaffold + schema Phase 2 additions** - `e537298` (test)
2. **Task 2: Chat backend module — conversation CRUD, memory retrieval, streaming router** - `eb43001` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/pytest.ini` - asyncio_mode = auto, testpaths = tests
- `backend/tests/__init__.py` - package marker
- `backend/tests/chat/__init__.py` - package marker
- `backend/tests/chat/test_conversation.py` - CHAT-01/02/03 unit tests (5 tests, all GREEN)
- `backend/tests/chat/test_memory.py` - CHAT-04 unit tests (2 tests, all GREEN)
- `backend/tests/chat/test_router.py` - UI-01 integration test stub (requires api/index.py from Plan 04)
- `backend/second_brain/chat/__init__.py` - package marker
- `backend/second_brain/chat/conversation.py` - CRUD: create, list, get_messages, save, build_messages_for_llm
- `backend/second_brain/chat/memory.py` - retrieve_memory_context with lazy get_embedding_provider wrapper
- `backend/second_brain/chat/router.py` - FastAPI APIRouter with 5 endpoints + SSE streaming
- `schema.sql` - Phase 2 additions: messages.embedding vector(1536), IVFFlat index, search_past_messages() function

## Decisions Made

- Module-level import of `get_db_client` in conversation.py so tests can patch it — `db.py` only imports supabase library at module load (no env var evaluation), making this safe
- Lazy wrapper function pattern for `get_embedding_provider` in memory.py — `embeddings.py` imports `cfg` at module level (triggers env var validation), so a wrapper function defers the real import to call time while still being patchable by name
- History capped at last 10 messages in `build_messages_for_llm` to prevent context window overflow
- Assistant responses saved with embeddings via fire-and-forget `asyncio.create_task` to avoid blocking SSE stream latency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test patchability for module-level lazy imports**
- **Found during:** Task 2 (GREEN verification run)
- **Issue:** Plan specified lazy imports inside every function body. `unittest.mock.patch("second_brain.chat.conversation.get_db_client")` fails with `AttributeError` when the name is not in the module namespace — lazy-only imports are invisible to `patch()`
- **Fix:** Imported `get_db_client` at conversation.py module level (safe — db.py doesn't trigger env vars). Created a lazy wrapper function `get_embedding_provider()` in memory.py for the embeddings import (which does trigger env vars via cfg) while still being patchable by name
- **Files modified:** backend/second_brain/chat/conversation.py, backend/second_brain/chat/memory.py
- **Verification:** All 5 tests pass GREEN
- **Committed in:** eb43001 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in import pattern for test patchability)
**Impact on plan:** Essential fix — tests could not run without it. No scope creep.

## Issues Encountered

- pytest and pytest-asyncio were not pre-installed; installed via pip before running Task 1 verification
- fastapi and httpx also installed (needed for test_router.py import of TestClient)

## User Setup Required

None — no external service configuration required for the backend module itself. The `api/index.py` FastAPI app entry point (needed for test_router.py to fully pass) will be created in Plan 02-04.

## Next Phase Readiness

- All 5 chat API endpoints implemented and importable without env vars
- test_conversation.py and test_memory.py: 5/5 tests passing GREEN
- test_router.py: requires `api/index.py` (Plan 02-04) for full pass — expected per plan
- schema.sql Phase 2 additions ready to apply to Supabase (idempotent ALTER TABLE + OR REPLACE FUNCTION)
- Plans 02-02 through 02-05 (frontend) can consume these endpoints

---
*Phase: 02-chat-ui-memory*
*Completed: 2026-03-10*

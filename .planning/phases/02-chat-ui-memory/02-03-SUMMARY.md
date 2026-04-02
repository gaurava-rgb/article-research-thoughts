---
phase: 02-chat-ui-memory
plan: "03"
subsystem: ui
tags: [nextjs, react, fastapi, readwise, sse, ingestion, tailwind, shadcn]

# Dependency graph
requires:
  - phase: 02-01
    provides: FastAPI router with POST /conversations, GET /conversations, GET /conversations/{id}/messages
  - phase: 02-02
    provides: ChatPanel, shadcn/ui components (Button, Separator), NewChatClient, ExistingChatClient stubs

provides:
  - POST /api/sync endpoint on FastAPI backend — triggers Readwise sync, returns status+message
  - IngestionPanel React component — collapsible panel with Readwise sync button and URL paste field
  - IngestionPanel wired into both /chat (NewChatClient) and /chat/[id] (ExistingChatClient) pages

affects:
  - 02-04 (Vercel deploy will serve the updated frontend with IngestionPanel)
  - 03 (Phase 3 URL ingestion pipeline will replace the placeholder URL field handler)

# Tech tracking
tech-stack:
  added:
    - fastapi (added to pyproject.toml — was missing despite router.py using it)
    - uvicorn[standard] (ASGI server, added alongside fastapi)
  patterns:
    - Lazy import for sync_readwise inside async endpoint (cold start optimization)
    - Thread executor for CPU/IO-bound sync in async FastAPI handler (asyncio.run_in_executor)
    - Collapsible panel with local React state (no global state needed for ingestion UI)

key-files:
  created:
    - frontend/src/components/IngestionPanel.tsx
  modified:
    - backend/second_brain/chat/router.py
    - backend/pyproject.toml
    - frontend/src/app/chat/NewChatClient.tsx
    - frontend/src/app/chat/[id]/ExistingChatClient.tsx

key-decisions:
  - "Sync runs synchronously in thread executor (not fire-and-forget) so UI shows real success/error result"
  - "URL ingestion field renders as UI placeholder only — backend pipeline deferred to Phase 3"
  - "fastapi and uvicorn added to pyproject.toml (were missing; router.py required them)"

patterns-established:
  - "Lazy import pattern for heavy ingestion dependencies inside route handlers"
  - "IngestionPanel is collapsed by default — user-initiated expansion keeps UI clean"

requirements-completed: [UI-05]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Phase 2 Plan 03: Ingestion Panel + /api/sync Summary

**Collapsible IngestionPanel with Readwise sync button wired to new POST /api/sync FastAPI endpoint, rendered above ChatPanel on both new and existing conversation pages**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T20:07:01Z
- **Completed:** 2026-03-10T20:12:00Z
- **Tasks:** 2
- **Files modified:** 5 (4 frontend, 1 backend router + 1 pyproject.toml)

## Accomplishments
- POST /api/sync endpoint added to FastAPI router — calls sync_readwise() in thread executor, returns JSON status
- IngestionPanel React component created with Readwise sync button (live feedback) and URL paste field (UI-05 placeholder)
- IngestionPanel rendered above ChatPanel in both /chat (new conversation) and /chat/[id] (existing conversation) layouts
- TypeScript compiles cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: POST /api/sync endpoint on FastAPI backend** - `eb7dfd4` (feat)
2. **Task 2: IngestionPanel component and wire into chat layout** - `1d6023c` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `backend/second_brain/chat/router.py` - Added POST /sync endpoint with thread-executor sync call
- `backend/pyproject.toml` - Added fastapi and uvicorn[standard] dependencies (were missing)
- `frontend/src/components/IngestionPanel.tsx` - Collapsible panel with sync button and URL field
- `frontend/src/app/chat/NewChatClient.tsx` - Added IngestionPanel above ChatPanel in new-chat layout
- `frontend/src/app/chat/[id]/ExistingChatClient.tsx` - Added IngestionPanel above ChatPanel in existing-chat layout

## Decisions Made
- Sync runs to completion before returning (not fire-and-forget) — gives user real success/error feedback in the UI
- URL ingestion field is a UI-only placeholder; shows informational message when submitted — Phase 3 backend scope
- Used shadcn/ui Button and Separator (already installed by 02-02) as specified in plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added fastapi and uvicorn to pyproject.toml**
- **Found during:** Task 1 (POST /api/sync endpoint)
- **Issue:** `fastapi` was not in pyproject.toml dependencies despite router.py importing from it; `uv run python` failed with ModuleNotFoundError
- **Fix:** Added `"fastapi"` and `"uvicorn[standard]"` to the dependencies list in pyproject.toml
- **Files modified:** backend/pyproject.toml
- **Verification:** `uv run python -c "from second_brain.chat.router import router"` succeeds; /sync route confirmed in router.routes
- **Committed in:** eb7dfd4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency)
**Impact on plan:** Necessary fix — FastAPI server cannot start without fastapi in dependencies. No scope creep.

## Issues Encountered
- Plan 02-02 was already executed (not mentioned in STATE.md which only showed 02-01 complete) — all shadcn/ui components and frontend chat files already existed. IngestionPanel was created using proper shadcn/ui Button and Separator as planned.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- POST /api/sync is ready; backend must have READWISE_TOKEN in environment for real sync to work
- IngestionPanel visible in chat UI on both /chat and /chat/[id]
- URL ingestion field is a placeholder; Phase 3 will implement the backend URL ingestion pipeline
- Plan 02-04 (Vercel deploy) can proceed — both frontend and backend are wired correctly

## Self-Check: PASSED

- FOUND: frontend/src/components/IngestionPanel.tsx
- FOUND: frontend/src/app/chat/NewChatClient.tsx (updated with IngestionPanel)
- FOUND: frontend/src/app/chat/[id]/ExistingChatClient.tsx (updated with IngestionPanel)
- FOUND: backend/second_brain/chat/router.py (POST /sync endpoint)
- FOUND: commit eb7dfd4 (Task 1 — backend sync endpoint)
- FOUND: commit 1d6023c (Task 2 — IngestionPanel wiring)
- FOUND: commit 0a742c3 (docs — SUMMARY + STATE + ROADMAP)
- TypeScript compilation: PASSED (no errors)
- Backend route verification: PASSED (/sync in router.routes)

---
*Phase: 02-chat-ui-memory*
*Completed: 2026-03-10*

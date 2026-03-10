---
phase: 02-chat-ui-memory
plan: 04
subsystem: infra
tags: [vercel, fastapi, nextjs, deployment, monorepo, cors, python]

# Dependency graph
requires:
  - phase: 02-chat-ui-memory
    provides: FastAPI chat router, Next.js frontend with chat UI, ingestion panel

provides:
  - api/index.py Vercel Python function entrypoint with FastAPI app and CORS middleware
  - vercel.json monorepo build config routing /api/* to FastAPI function
  - .gitignore root-level gitignore for env files, build artifacts, and Python cache
  - frontend/.env.local local dev environment marker (gitignored, created on disk only)

affects: [deployment, production, vercel, public-url]

# Tech tracking
tech-stack:
  added: [vercel (deployment platform), CORSMiddleware (fastapi)]
  patterns: [vercel-monorepo-pattern, lazy-router-import, sys-path-injection-for-backend]

key-files:
  created:
    - api/index.py
    - vercel.json
    - .gitignore
    - frontend/.env.local (gitignored; on disk only)
  modified: []

key-decisions:
  - "api/index.py at repo root is mandatory Vercel Python function entrypoint — Vercel requires exactly this path"
  - "maxDuration: 300 in vercel.json sets Hobby plan maximum — needed for Readwise sync (60-120s) and LLM streaming"
  - "CORS allow_origins includes localhost:3000 only; Vercel domain added post-deploy"
  - "frontend/.env.local not committed to git (correctly gitignored) — exists on disk for local dev only"
  - ".gitignore/ directory (accidentally created, untracked) removed and replaced with proper .gitignore file"

patterns-established:
  - "sys.path.insert to backend/ in api/index.py: standard pattern for Vercel + local FastAPI monorepo"
  - "Lazy router import via _include_router() function: defers heavy backend imports to avoid cold start cost"

requirements-completed: [UI-07]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 2 Plan 4: Vercel Deployment Configuration Summary

**FastAPI Vercel entrypoint (api/index.py) and monorepo build config (vercel.json) ready for single-command `vercel --yes` deployment of Next.js + FastAPI second brain**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T20:32:38Z
- **Completed:** 2026-03-10T20:38:00Z
- **Tasks:** 1 of 2 complete (checkpoint reached — human verification required)
- **Files modified:** 3 committed, 1 on disk (gitignored)

## Accomplishments
- Created `api/index.py` — Vercel-compliant Python function entrypoint with FastAPI app, CORS middleware (localhost:3000), and lazy router import pattern
- Created `vercel.json` — monorepo build config pointing to `frontend/` with `/api/*` rewrites and 300s function timeout for Hobby plan
- Created root `.gitignore` covering env files, `.vercel/`, Python cache, Next.js artifacts, and macOS `.DS_Store`
- Removed accidental `.gitignore/` directory (was untracked, contained local `.env` file) and replaced with proper file

## Task Commits

Each task was committed atomically:

1. **Task 1: Create api/index.py and vercel.json** - `ef133d9` (chore)

## Files Created/Modified
- `api/index.py` — FastAPI Vercel entrypoint; imports router lazily and mounts at /api prefix; adds CORS for local dev
- `vercel.json` — Routes /api/* to FastAPI function; sets frontend build command and output dir; maxDuration: 300
- `.gitignore` — Root-level gitignore (replaced accidental directory); covers all standard exclusions
- `frontend/.env.local` — On disk only (gitignored); minimal development environment marker

## Decisions Made
- Removed accidentally-created `.gitignore/` directory (untracked, contained only a local `.env` file with Supabase credentials — not committed to git, no security issue)
- `frontend/.env.local` intentionally not committed to git per `.gitignore` rules — correct behavior for env files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed accidental .gitignore/ directory before creating .gitignore file**
- **Found during:** Task 1 (Create api/index.py and vercel.json)
- **Issue:** `.gitignore/` was a directory (untracked) at the repo root — git showed it as `?? .gitignore/`. Could not create a `.gitignore` file while a directory with that name existed.
- **Fix:** Removed the directory (`rm -rf .gitignore/`) then created the proper `.gitignore` file
- **Files modified:** `.gitignore` (created as file; directory removed)
- **Verification:** `git status` confirms `.gitignore` tracked as file; directory gone
- **Committed in:** ef133d9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** Required fix to unblock .gitignore creation. No scope creep.

## Issues Encountered
- `frontend/.env.local` could not be committed because `.gitignore` correctly excludes it. This is expected — env files should not be committed.

## User Setup Required

**External services require manual configuration before deploying.**

In Vercel Dashboard -> Your Project -> Settings -> Environment Variables, add:
- `SUPABASE_URL` — Supabase Project URL (Dashboard -> Project Settings -> API -> Project URL)
- `SUPABASE_KEY` — Supabase service_role key (Dashboard -> Project Settings -> API -> service_role key)
- `OPENROUTER_API_KEY` — OpenRouter API key (OpenRouter Dashboard -> Keys)
- `READWISE_TOKEN` — Readwise access token (https://readwise.io/access_token)

Then deploy:
```bash
npm install -g vercel
cd /path/to/repo
vercel --yes
```

Apply Phase 2 schema additions to production Supabase (SQL editor -> run the "Phase 2 Additions" block from schema.sql).

## Next Phase Readiness
- Deployment config complete — awaiting human verification of live Vercel URL
- Once checkpoint confirmed, UI-07 requirement is fully satisfied
- Phase 3 (Clustering + Topic Evolution) can begin after this plan completes

---
*Phase: 02-chat-ui-memory*
*Completed: 2026-03-10*

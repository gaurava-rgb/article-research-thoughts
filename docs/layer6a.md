# Layer 6a: V2 Deploy Log — What Was Done

## Date: 2026-04-03

## What Was Deployed

The analyst workbench (V2) was deployed to Vercel production. This includes:
- Entity extraction pipeline (`extraction.py`)
- Entity workbench UI (`/entities`, `/entities/[id]`)
- Dossier pages with timelines, evidence, relationships
- Insights and suggestions system
- Improved chat with `[FROM SOURCES]` / `[ANALYSIS]` / `[CONTRADICTIONS]` format
- Topic clustering
- Enhanced Readwise ingestion with kind/tier/publisher metadata

## Deploy Sequence (What Was Done, In Order)

### Step 1: Verified Environment Variables
All 4 env vars confirmed set in Vercel dashboard:
- [x] `SUPABASE_URL`
- [x] `SUPABASE_KEY`
- [x] `OPENROUTER_API_KEY`
- [x] `READWISE_TOKEN`

### Step 2: Ran 3 SQL Migrations on Supabase
Run in order in the Supabase SQL editor:

1. **`migrations/2026-04-02-phase1-analyst-foundation.sql`**
   - Added columns to `sources`: external_id, kind, tier, publisher, metadata, checksum, etc.
   - Added columns to `chunks`: kind, section_label, speaker, start_char, end_char, metadata
   - Created `processing_runs` table
   - **Dropped and recreated `hybrid_search`** function with new signature (returns kind, tier, publisher)
   - Result: SUCCESS

2. **`migrations/2026-04-02-phase2-claims-and-evidence.sql`**
   - Created: `entities`, `entity_aliases`, `source_entities`, `lenses` (with 10 seed frameworks)
   - Created: `claims`, `claim_lenses`, `claim_evidence`, `claim_links`
   - Result: SUCCESS

3. **`migrations/2026-04-02-phase3-dossier-and-timeline.sql`**
   - Created: `entity_relationships`
   - Created: `entity_claim_timeline` view (UNION of subject + object entity claims)
   - Result: SUCCESS

### Step 3: Merged Branch
```
git merge codex-post-v1-analyst-workbench --no-edit
```
- Fast-forward merge, no conflicts
- 102 files changed, +27,356 lines, -507 lines
- Branch: `codex-post-v1-analyst-workbench` -> `main`

### Step 4: Deployed to Vercel
```
vercel --prod --yes
```
- Build time: 43 seconds
- Next.js 16.1.6 compiled successfully (Turbopack, 8.4s)
- Routes built: `/`, `/chat`, `/chat/[id]`, `/entities`, `/entities/[id]`
- Python serverless function installed from `api/requirements.txt`
- Production URL: https://article-research-thoughts.vercel.app

### Step 5: Verified All Endpoints

| Endpoint | Status | Result |
|----------|--------|--------|
| `GET /api/entities` | ✅ Working | 18 entities returned (OpenClaw, Sam, Claire, Acme, etc.) with claim counts and aliases |
| `GET /api/insights` | ✅ Working | Empty (no insights generated yet — expected) |
| `GET /api/topics` | ✅ Working | 20+ topic clusters with article counts |
| `GET /api/conversations` | ✅ Working | 50 conversations (V1 data preserved) |

## What's Now Available

### New Pages
- `/entities` — Entity directory (searchable grid of all extracted entities)
- `/entities/[id]` — Entity dossier (thesis, timeline, evidence, relationships)

### New API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/entities` | Entity directory listing |
| `GET` | `/api/entities/{entity_id}` | Full entity dossier with timeline |
| `GET` | `/api/sources/{source_id}` | Source detail + analysis data |
| `POST` | `/api/sources/{source_id}/analyze` | Run entity/claim extraction on a source |
| `GET` | `/api/topics` | List all topics with article counts |
| `GET` | `/api/insights` | List active insights |
| `PATCH` | `/api/insights/{insight_id}/seen` | Mark insight as seen |
| `POST` | `/api/insights/generate-digest` | Generate weekly reading digest |
| `POST` | `/api/insights/generate-suggestions` | Generate research suggestions |
| `GET` | `/api/conversations/similar` | Find similar past conversations |

### Pre-existing Data
The analyst workbench branch had already run extraction on some sources:
- 18 entities extracted (companies, people, products, technologies, publications)
- Claims with evidence, links, and lenses attached
- Entity aliases (e.g., "Acme Corp" -> "Acme")

## Post-Deploy Fixes (2026-04-03, same session)

### Bug: Dynamic routes 404'd in production
After deploying, clicking any entity dossier (`/entities/[id]`) or chat conversation
(`/chat/[id]`) returned a Vercel 404. Static pages (`/entities`, `/chat`) worked fine.

**Root cause:** The legacy `builds` + `routes` Vercel config registered dynamic Next.js
serverless functions as `frontend/entities/[id]` and `frontend/chat/[id]`. The catch-all
route `/(.*) → /frontend/$1` rewrote `/entities/abc123` to `/frontend/entities/abc123`
(a literal path), which Vercel couldn't match to the `[id]` function.

**Complicating factor:** During debugging, the GitHub repo was made private, which caused
Vercel's Hobby plan to block all new deployments with:
> "Git author must have access to the team's projects. Hobby plan does not support
> collaboration for private repositories."

This caused 5–6 consecutive `[0ms]` "Unexpected error" build failures that looked like
config errors but were actually an auth/billing block.

**Fix sequence:**
1. Made GitHub repo public (`gh repo edit --visibility public`)
2. Added explicit dynamic routes in `vercel.json` before the catch-all:
   ```json
   { "src": "/entities/([^/]+)", "dest": "/frontend/entities/[id]?id=$1" },
   { "src": "/chat/([^/]+)",     "dest": "/frontend/chat/[id]?id=$1"     }
   ```
3. Deployed — all routes now 200.

**Commit:** `4fb50b9` — `fix(routing): route dynamic Next.js pages to serverless function paths`

### Final verified state (all green)

| Route | Status |
|-------|--------|
| `/entities` | ✅ 200 |
| `/entities/[id]` | ✅ 200 |
| `/chat` | ✅ 200 |
| `/chat/[id]` | ✅ 200 |
| `/api/entities` | ✅ 200 |
| `/api/insights` | ✅ 200 |
| `/api/topics` | ✅ 200 |
| `/api/conversations` | ✅ 200 |

### GitHub repo
- URL: https://github.com/gaurava-rgb/article-research-thoughts
- Visibility: **Public** (required for Vercel Hobby plan)
- Branches pushed: `main`, `codex-post-v1-analyst-workbench`
- Note: The repo does NOT drive Vercel deploys (no GitHub integration). Deploys are
  done manually via `vercel --prod --yes` from the repo root.

## What's NOT Done Yet

- [ ] LightRAG sidecar (no code exists — needs VPS + Docker + sync adapter)
- [ ] Bulk extraction on remaining sources (only ~1 source has been analyzed)
- [ ] Insight/suggestion generation (endpoints exist but nothing generated yet)
- [ ] Debug exception handler still exposed in production (`api/index.py`)
- [ ] No auth on any endpoint
- [ ] No health check endpoint

## How to Deploy Going Forward

```bash
cd /Users/gauravarora/Documents/Articleresearchthoughts
vercel --prod --yes
# then push to GitHub to keep it in sync:
git push origin main
```

Note: Vercel is NOT connected to GitHub auto-deploy. Always run `vercel --prod` explicitly.

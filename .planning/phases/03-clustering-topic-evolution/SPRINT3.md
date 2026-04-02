# Sprint 3 — Clustering + Topic Evolution

**Goal:** Articles auto-organize into topics on ingestion. No manual tagging.
**Phase:** 03
**Started:** 2026-04-01
**Status:** In progress

---

## Current State (verified 2026-04-01)

| Item | Status | Notes |
|------|--------|-------|
| `clustering.py` | DONE | Fully implemented, not a stub |
| `tests/clustering/` | DONE | 13 tests, all passing |
| DB schema (topics.centroid_embedding + match_topic) | DONE | Applied 2026-04-01 |
| GET /api/topics endpoint | TODO | Not in router.py |
| Wire clustering into sync CLI | TODO | `assign_topics` exists as standalone command but not called during sync |
| Full test suite | BROKEN | 6 failures (see Task 0 below) |

---

## Tasks

### Task 0 — Fix failing tests (pre-condition) ✅ / ❌
**Status:** TODO
**Why it matters:** These failures make it hard to tell if Phase 3 work breaks anything.

Failures:
- `tests/chat/test_router.py` x2 → `ModuleNotFoundError: No module named 'api'` (test import issue)
- `tests/ingestion/test_readwise.py` x2 → `ModuleNotFoundError: No module named 'second_brain'` (same)
- `tests/test_cli.py::test_sync_repairs_missing_chunks_even_when_no_new_articles` → TBD
- `tests/test_cli.py::test_assign_topics_processes_unassigned_sources` → `AttributeError: module 'second_brain.providers' has no attribute 'llm'` (patch target wrong)

**Fix:** Diagnose each — likely all import/path issues not real bugs.

**Verify:**
```bash
cd backend && uv run pytest tests/ -q
# Expected: 0 failures (22+ passed)
```

---

### Task 1 — Verify DB schema in Supabase
**Status:** DONE — ran schema.sql lines 173-239 in Supabase on 2026-04-01
**Why it matters:** clustering.py calls `match_topic` via `db.rpc()` and reads `topics.centroid_embedding`. If these don't exist in Supabase, sync will crash at Step 4.

**SQL to run in Supabase SQL Editor:**
```sql
-- Add centroid_embedding to topics (safe to run even if already exists)
ALTER TABLE topics ADD COLUMN IF NOT EXISTS centroid_embedding vector(1536);

-- Create match_topic function
CREATE OR REPLACE FUNCTION match_topic(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.65,
  match_count int DEFAULT 1
)
RETURNS TABLE (topic_id uuid, topic_name text, similarity float)
LANGUAGE sql STABLE AS $$
  SELECT
    id AS topic_id,
    name AS topic_name,
    1 - (centroid_embedding <=> query_embedding) AS similarity
  FROM topics
  WHERE centroid_embedding IS NOT NULL
    AND 1 - (centroid_embedding <=> query_embedding) >= match_threshold
  ORDER BY centroid_embedding <=> query_embedding
  LIMIT match_count;
$$;
```

**Verify (run in Supabase SQL Editor):**
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'topics' AND column_name = 'centroid_embedding';
-- Expected: 1 row

SELECT routine_name FROM information_schema.routines
WHERE routine_name = 'match_topic';
-- Expected: 1 row
```

---

### Task 2 — Add GET /api/topics endpoint to router.py
**Status:** TODO
**File:** `backend/second_brain/chat/router.py`

**What it returns:**
```json
[
  {"id": "uuid", "name": "Machine Learning Fundamentals", "summary": "...", "article_count": 12},
  ...
]
```
Sorted by `article_count` DESC.

**Implementation:** Two queries — fetch all topics, fetch all source_topics, merge counts.

**Verify:**
```bash
# Import check
cd backend && uv run python -c "
from second_brain.chat.router import router
routes = [r.path for r in router.routes]
assert '/api/topics' in routes, f'Missing. Routes: {routes}'
print('GET /api/topics registered OK')
"

# Full test suite still passes
uv run pytest tests/ -q
```

---

### Task 3 — Wire clustering into sync command (Steps 4 + 5)
**Status:** TODO
**File:** `backend/second_brain/cli.py`

**What to add** (after the Step 3 chunking loop):

**Step 4 — Topic assignment** (once per newly synced source):
```python
console.print("\n[cyan]Step 4:[/cyan] Assigning articles to topics...")
from second_brain.ingestion.clustering import assign_topic_to_source
from second_brain.providers.llm import get_llm_provider
llm_provider = get_llm_provider()

changed_topic_ids: set[str] = set()
for source_id in newly_stored_source_ids:
    result = assign_topic_to_source(source_id, db, llm_provider)
    if result.topic_id:
        changed_topic_ids.add(result.topic_id)
        status = "new topic" if result.created_topic else f"→ existing (sim={result.similarity:.2f})"
        console.print(f"  [dim]{source_id[:8]}[/dim]: {status}")
```

**Step 5 — Summary regeneration** (once per *changed topic*, not per article):
```python
console.print("\n[cyan]Step 5:[/cyan] Updating topic summaries...")
from second_brain.ingestion.clustering import regenerate_topic_summary  # if it exists
# OR: just fetch titles and call llm.complete once per topic
for topic_id in changed_topic_ids:
    # fetch titles of all sources in this topic
    rows = db.table("source_topics").select("sources(title)").eq("topic_id", topic_id).execute().data
    titles = [r["sources"]["title"] for r in rows if r.get("sources")][:30]
    summary = llm_provider.complete([
        {"role": "system", "content": "You write brief topic summaries for a personal knowledge base. 2-3 sentences max."},
        {"role": "user", "content": f"Topic sources:\n" + "\n".join(f"- {t}" for t in titles)},
    ])
    db.table("topics").update({"summary": summary}).eq("id", topic_id).execute()
    console.print(f"  Updated summary for topic {topic_id[:8]}")
```

**Important:** Wrap Steps 4+5 in `try/except Exception` — sync must not fail if clustering fails.

**Verify:**
```bash
# Import check
cd backend && uv run second-brain sync --help
# Expected: no ImportError, shows help

# Full test suite
uv run pytest tests/ -q
```

---

### Task 4 — Human verify end-to-end (blocking)
**Status:** TODO — human required
**Depends on:** Tasks 1, 2, 3 all done

**Steps:**

1. Run sync with small limit:
   ```bash
   cd backend && uv run second-brain sync --limit 5
   ```
   Expected: Steps 1-5 all print, Step 4 shows per-article topic assignments, Step 5 shows updated summaries. No errors.

2. Check Supabase:
   - `topics` table: 1+ rows with name and summary populated
   - `source_topics` table: rows linking source UUIDs to topic UUIDs

3. Test idempotency (re-run):
   ```bash
   uv run second-brain sync --limit 5
   ```
   Expected: "0 new articles" — no duplicate topic assignments.

4. Test the API (backend must be running):
   ```bash
   curl http://localhost:8000/api/topics | python3 -m json.tool | head -30
   ```
   Expected: JSON array with id/name/summary/article_count.

5. Full test suite:
   ```bash
   uv run pytest tests/ -q
   ```
   Expected: all pass.

**Resume signal:** Type "verified" or "issues: [description]"

---

## What Remains After Sprint 3

| Phase | What | Key deliverable |
|-------|------|----------------|
| Phase 4 | Synthesis Engine | Narrative answers that synthesize across multiple sources, separated "FROM YOUR SOURCES" vs "LLM ANALYSIS" sections, contradiction detection |
| Phase 5 | Proactive Insights + Digests | Weekly digest, unseen insight badge in UI, system notices patterns without being asked |

---

## Progress Log

| Date | What happened |
|------|--------------|
| 2026-03-10 | Phase 3 planned. clustering.py stub + 7 failing tests per plan. |
| 2026-04-01 | Found clustering.py fully implemented (13 tests passing). 6 test suite failures. /api/topics missing. sync not wired. Sprint file created. |
| 2026-04-01 | Task 1 done — ran schema.sql lines 173-239 in Supabase. topics.centroid_embedding + match_topic function now live. |
| 2026-04-01 | Task 0 done — fixed all 6 test failures: installed pytest into venv, created api/__init__.py + api/index.py, fixed store_articles 2-tuple unpack, fixed get_last_ingested_at mock, fixed stale backfill_missing_chunks assertions. 28/28 passing. |
| 2026-04-01 | Task 2 done — GET /api/topics added to router.py. Returns id/name/summary/article_count sorted by count desc. |
| 2026-04-01 | Task 3 done — Steps 4+5 wired into sync CLI. assign_topic_to_source called per new article, topic summaries regenerated per changed topic, wrapped in try/except. |
| 2026-04-01 | Task 4 done — human verified. Fixed Supabase vector string bug (_parse_embedding helper added to clustering.py). assign-topics backfill: 764 sources → 354 topics. Idempotency confirmed. /api/topics returning correct JSON. Sprint 3 complete. |

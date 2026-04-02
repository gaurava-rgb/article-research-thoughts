# Now

## Current Goal

Implement a dedicated backfill or repair path for rows where `sources.source_embedding` is still NULL, so broad Phase 3 clustering can rely on article-level vector coverage across the corpus.

## Why

The source-level embedding prerequisite is materially working for newly inserted rows, but the documented verified state still shows a meaningful older slice without `source_embedding`. Broad topic clustering should not silently exclude those sources.

## In Scope

- choose the smallest safe backfill or repair approach for missing `source_embedding`
- implement that repair path without broad clustering work
- keep the logic consistent with the existing whole-source embedding write path
- verify what the repair path should and should not touch

## Out Of Scope

- topic clustering or assignment itself
- topic summaries
- topic endpoints or UI
- retrieval ranking changes
- broad ingestion refactors beyond what is required for source-embedding repair
- chunk repair beyond what is strictly necessary for this task

## Current State

- Phase 1: complete
- Phase 2: functionally complete and first-run UX is improved
- Phase 3: first backend prerequisite is now working in the live system
- old Phase 3 planning text has now been reconciled to the `sources.source_embedding` design
- `topics` and `source_topics` exist in schema but are not used yet
- Reader sync now requests `withHtmlContent=true` and falls back to extracted `html_content` text when `content` is null
- source-level embedding input is truncated to a safe token budget for large documents
- live database verification during this session reached:
  - `714` rows in `sources`
  - `643` rows in `sources` with non-null `source_embedding`
  - `1800` rows in `chunks`
- some synced sources still have `source_embedding` but no chunks yet because browser-triggered sync is a long-running request path
- missing chunks were assessed as a reliability issue, but not the immediate blocker to broad clustering
- missing `source_embedding` rows were assessed as the immediate blocker to broad clustering rollout

## Likely Files

- `schema.sql`
- `backend/second_brain/cli.py`
- `backend/second_brain/chat/router.py`
- `backend/second_brain/ingestion/readwise.py`
- `backend/second_brain/ingestion/chunker.py`
- `backend/second_brain/providers/embeddings.py`
- `backend/tests/`

## Done Means

- there is an explicit supported way to fill missing `sources.source_embedding` values for older rows
- the repair path reuses the same whole-source embedding assumptions as the current sync path
- the task stops before topic assignment begins
- the docs clearly reflect whether the repair path is CLI-based, one-shot, or both

## Verified

- schema reflects source-level embedding storage
- targeted ingestion tests cover:
  - new-source embedding writes
  - `html_content` fallback when `content` is null
  - truncation of large source text before embedding
  - duplicate insert race handling as `skipped`
- live sync writes source embeddings for newly inserted Reader documents
- live DB state shows the source-level embedding prerequisite is materially working
- subagent review concluded that broad clustering should not roll out until older NULL `source_embedding` rows have a repair path
- subagent review concluded that missing chunks are important but not the first blocker to solve

## Next Decision

Choose the smallest concrete implementation for source-embedding repair:

- dedicated CLI backfill command
- repair mode added to existing sync flow
- one-shot operational script with tests

## Prompt To Use

```md
Read `CURSORPLAN.md`, `docs/PROJECT.md`, `docs/NOW.md`, and `docs/DECISIONS.md`.
Read `docs/PROGRESS.md` for the latest verified state.

Summarize:
- what is already complete
- why `source_embedding` backfill is now the next task
- the smallest repair-path implementation

Do not begin topic assignment, clustering, summaries, retrieval changes, or UI work unless `docs/NOW.md` is explicitly advanced to that task.
Before declaring the task complete, run the mandatory closeout in `docs/CLOSEOUT.md` and report which docs were updated.
```

## Stop After

Stop after the source-embedding repair path is implemented and documented.

Do not continue into:

- topic clustering
- topic summaries
- topic endpoints
- frontend topic UI
- broad backend cleanup

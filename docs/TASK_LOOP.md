# Task Loop

Use this as the day-to-day control panel.

You should be able to:

1. open this file
2. pick the active task
3. start a fresh chat
4. get the task done
5. come back here
6. update this file
7. pick the next task

If you want a simpler workflow, use this file first and treat the other docs as reference material.

## How To Use

### Step 1

If `ACTIVE TASK` is filled, use that.

If `ACTIVE TASK` is empty, take the first item from `NEXT TASKS` and move it into `ACTIVE TASK`.

### Step 2

Start a fresh chat and paste the prompt from `CHAT PROMPT`.

### Step 3

Let the agent do only that task.

### Step 4

When the task is done, come back to this file and update:

- `STATUS`
- `RESULT`
- `DONE RECENTLY`
- `NEXT TASKS`

### Step 5

Start a new fresh chat for the next task.

Rule:

One task per chat.

## CHAT PROMPT

```md
Read `docs/TASK_LOOP.md` first.

Then read only the reference docs needed for the active task:
- `docs/PROJECT.md`
- `docs/DECISIONS.md`
- `docs/PROGRESS.md`
- `docs/ARCHITECTURE.md` only if needed

Work only on the `ACTIVE TASK` from `docs/TASK_LOOP.md`.

Before ending the task:
- update `docs/TASK_LOOP.md`
- update `docs/PROGRESS.md`
- update `docs/DECISIONS.md` if a real decision was made
- update any other docs only if they genuinely changed

Do not continue into the next task.
Report exactly which files you updated.
```

## ACTIVE TASK

### Title

Fold topic assignment into normal sync in the smallest safe way.

### Why

Manual `assign-topics` now works, but Phase 3 still depends on a separate command to keep the corpus organized. The next step is to make fresh syncs advance topic structure automatically without dragging in summaries, UI work, or a broader background-job redesign.

### Scope

- decide the smallest place normal sync should trigger topic assignment
- wire that path so newly ingested or still-unassigned sources can be assigned during the regular sync flow
- preserve the current Phase 3 design: reuse source embeddings, centroid matching, durable `source_topics` writes, and resumable behavior
- stop before topic summaries, topic UI, synthesis-layer work, or a larger worker/job architecture

### Likely Files

- `backend/second_brain/ingestion/readwise.py`
- `backend/second_brain/ingestion/clustering.py`
- `backend/second_brain/chat/router.py`
- `backend/tests/ingestion/test_readwise.py`
- `backend/tests/clustering/`
- `backend/second_brain/cli.py`
- `docs/PROGRESS.md`
- `docs/DECISIONS.md`
- `docs/TASK_LOOP.md`

### Done Means

- normal sync has one deliberate path that advances topic assignment without requiring a separate manual step
- assignment remains consistent with the current source-level embedding and centroid-matching design
- the task stops before topic summaries, topic APIs/UI, or broader background processing work

### Status

ready to start

### Result

not started yet

## NEXT TASK CARDS

Use these as the ready queue.

When the active task is done:

1. copy the next task card into `ACTIVE TASK`
2. remove it from this queue
3. start a fresh chat with the existing prompt

No queued task cards right now.

## DONE RECENTLY

- Added the first durable Phase 3 topic-assignment pass with explicit CLI execution, existing-topic matching, new-topic creation, and durable `source_topics` membership writes without yet wiring assignment into normal sync.
- Implemented the first true Phase 3 topic-structure foundation by adding topic centroid storage, SQL topic matching, and tested backend clustering helpers without yet wiring full assignment orchestration.
- Reconciled stale SSE-era chat wording so the active `/api/chat` path, frontend helpers, and progress docs now consistently describe a single JSON response.
- Made long-running `/api/sync` behavior more honest in the UI by distinguishing uncertain request endings from definite backend failures.
- Standardized zero-chunk repair as shared sync behavior so both CLI and UI sync can heal partial-progress corpus state, including no-new-article CLI runs.
- Added an explicit backfill path for older rows missing `sources.source_embedding`.
- Reconciled old Phase 3 planning text to the `sources.source_embedding` reality.
- Decided that missing `source_embedding` rows require a dedicated backfill path before broad clustering rollout.
- Decided that missing chunks are important but not the first blocker to solve.

## WHEN YOU RETURN AFTER A TASK

Update this file like this:

1. change `Result`
2. change `Status`
3. move the finished task into `DONE RECENTLY`
4. move the next item from `NEXT TASKS` into `ACTIVE TASK`
5. keep the list ordered

## IF A TASK FAILS OR GETS BLOCKED

Do not silently switch tasks.

Instead update:

- `Status: blocked`
- `Result: blocked because ...`

Then either:

- retry the same task in a new chat
- or rewrite the active task into a smaller one

## Reference Docs

Use these only when needed:

- `docs/PROJECT.md` for product truth
- `docs/ARCHITECTURE.md` for system design
- `docs/DECISIONS.md` for past choices
- `docs/PROGRESS.md` for recent verified work
- `docs/TODO.md` for the bigger backlog

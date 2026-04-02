# Progress

## 2026-04-02

### Completed (repair-chunks carry-over + embedding skip fix)

- ran `second-brain repair-chunks` to fix 147 unchunked tweet sources (Sprint 5 carry-over)
- result: 59 sources repaired, 285 chunks created, 1 skipped
- 1 skipped source had epub/CSS junk content (`@charset "UTF-8"...`) — leaked through ingestion, not embeddable
- fixed `backfill_missing_chunks` in `readwise.py` to catch embedding failures per-source and skip+log instead of crashing the whole run
- **File:** `backend/second_brain/ingestion/readwise.py` (try/except around `store_chunks_with_embeddings`)

### DB state (2026-04-02, post repair-chunks)

- Sources: 765
- Chunks: ~3,674 (3,389 pre-run + 285 new)
- Unchunked sources remaining: ~9 (1 bad epub + ~8 unknown)
- Sprint 5 carry-over is complete — corpus is now ready for digest/Phase 5 work

## 2026-03-23

### Completed (manual topic assignment mechanics)

- extended `backend/second_brain/ingestion/clustering.py` from centroid foundations into true assignment helpers for: source lookup, LLM naming for new topics, durable `source_topics` inserts, and batch assignment of unassigned sources
- added an explicit `second-brain assign-topics` CLI command so Phase 3 topic assignment can run intentionally without yet changing normal sync behavior
- expanded focused tests to cover topic-name cleanup, durable membership writes, existing-topic assignment, new-topic creation, unassigned-source batch processing, and the new CLI command

### Verified

- `PYTHONPATH=backend:. pytest backend/tests/clustering/test_clustering.py backend/tests/test_cli.py -q` passes
- `PYTHONPATH=backend:. pytest backend/tests/clustering/test_clustering.py backend/tests/ingestion/test_readwise.py backend/tests/chat/test_router.py backend/tests/test_cli.py -q` passes
- the task stops before sync orchestration, topic summaries, topic APIs, or topic UI work

### Next

- next task: fold topic assignment into normal sync in the smallest safe way
- stop before topic summaries, topic UI, synthesis-layer work, or broader background-job architecture

### Completed (Phase 3 centroid + matching foundation)

- added `topics.centroid_embedding` to `schema.sql` for durable topic-level vectors on fresh and existing databases
- added a `match_topic` SQL helper so topic lookup can consistently compare a source embedding against stored centroids
- created `backend/second_brain/ingestion/clustering.py` with the smallest true Phase 3 backend helpers: source-embedding lookup, topic matching, centroid recomputation, and date-filtered topic source retrieval
- added focused clustering tests covering centroid persistence, RPC-based topic matching, and temporal topic-source filtering behavior

### Verified

- `PYTHONPATH=backend:. pytest backend/tests/clustering/test_clustering.py -q` passes
- `PYTHONPATH=backend:. pytest backend/tests/clustering/test_clustering.py backend/tests/ingestion/test_readwise.py backend/tests/chat/test_router.py backend/tests/test_cli.py -q` passes
- this task stops before full topic assignment, new topic creation, sync orchestration, topic UI, or synthesis work

### Next

- next task: add topic matching and assignment logic on top of the new centroid/matching foundation
- stop before topic summaries, topic UI, or synthesis-layer work unless that narrower assignment task proves impossible without them

### Completed (honest long-running sync UI)

- updated `IngestionPanel` copy to explain that large Readwise syncs can outlast a single browser request
- changed sync UI state handling so a dropped or unresolved browser request is shown as uncertain rather than as a definite backend failure
- updated the running-state button and status copy to describe waiting on the current request, not the entire sync lifecycle

### Verified

- `cd frontend && npm run lint -- src/components/IngestionPanel.tsx` passes
- the sync panel now distinguishes `complete`, `warning`, and `error` states instead of collapsing all non-success outcomes into a single failure message
- the fallback message for fetch interruption now explicitly tells the user that backend sync work may still be continuing

### Completed (shared chunk-repair sync behavior)

- added a shared ingestion helper that repairs stored `sources` rows still missing any `chunks`
- removed the CLI sync early-exit behavior that previously skipped chunk repair when a run inserted no new articles
- updated the UI `/api/sync` path to reuse the same zero-chunk repair helper instead of maintaining a separate repair loop
- added focused test coverage for zero-chunk repair selection, CLI no-new-article repair behavior, and current `/api/chat` JSON response expectations

### Verified

- focused backend tests pass: `PYTHONPATH=backend:. pytest backend/tests/ingestion/test_readwise.py backend/tests/chat/test_router.py backend/tests/test_cli.py`
- rerunning CLI sync now still attempts chunk repair even when `store_articles()` reports `0` new articles
- CLI and UI sync now share the same bounded chunk-repair path for partial-progress corpus healing

### Completed

- reviewed the repo and GSD planning artifacts from a product and architecture perspective
- confirmed the current app is best described as enhanced RAG plus memory, not yet a full second-brain system
- identified that the Phase 2 frontend is requirement-complete but weak in product feel
- created a lightweight Cursor-native documentation system to replace phase-heavy daily execution

### Verified

- Phase 1 is complete in planning and implementation terms
- Phase 2 backend and core UI shell exist
- Phase 3 is planned but not yet started
- future product intent for Phase 4 and Phase 5 is real, but needed clearer durable specs outside GSD plan flow

### Completed (first-run UX improvements)

- **NewChatClient**: Replaced bare "Starting conversation..." with guided loading state (spinner, "Setting up your chat", "One moment...")
- **ExistingChatClient**: Replaced bare "Loading conversation..." with intentional loading state (spinner, "Loading conversation", "Fetching your messages...")
- **ChatPanel**: Improved empty-state copy ("What would you like to explore?", value prop); simplified placeholder; Send shows "Thinking…" while a reply is pending
- **ConvSidebar**: Clearer header ("Conversations"), New Chat button with icon, guided empty state ("Start a new chat to begin. Your conversations will appear here.")
- **IngestionPanel**: Honest copy for URL—"Add by URL (coming soon)" label; message "Add by URL is coming soon. Use Readwise sync to add articles now."; subtle panel polish

### Known Issues

- URL ingestion in the UI is still a placeholder (copy is now honest)
- current chat path is too monolithic for eventual synthesis complexity
- proactive insight features will require background workflow architecture

### Current Workflow Decision

Use a doc-driven Cursor workflow:

- `CURSORPLAN.md` is the entrypoint
- `docs/NOW.md` controls the active task
- `docs/SPECS/` holds deeper future-phase design

### Next

- first-run UX task is complete and `docs/NOW.md` has been advanced
- next task: add source-level embeddings during sync as the first Phase 3 prerequisite
- stop before topic assignment, clustering, summaries, or UI work

### Completed (source-level sync embeddings)

- added durable `source_embedding` storage to `sources` in `schema.sql`
- updated sync storage so newly inserted Readwise articles persist one whole-source embedding before chunk work
- kept the chunking and chunk-embedding path unchanged after source insert
- added a focused ingestion test covering new-source embedding writes while skipped articles remain untouched
- fixed the `/api/sync` backend path so UI-triggered sync also writes `source_embedding` for newly inserted sources
- added logging for Readwise fetch totals and short-content filtering so future sync mismatches are visible
- fixed Reader ingestion to request `withHtmlContent=true` and fall back to extracted `html_content` text when `content` is null for newer saved documents
- capped whole-source embedding input to a safe token budget so large Reader documents do not fail source embedding during sync
- hardened source inserts so duplicate `readwise_id` races are treated as `skipped` instead of aborting the whole sync

### Verified (live runtime state)

- Reader API investigation showed the real issue was not the wrong endpoint, but that newer Reader documents often returned `content = null` unless `html_content` was explicitly requested
- direct verification against a recent WIRED article showed `content` was null while `html_content` contained the full article body
- live sanity check after the Reader API fix showed the current token yields `714` ingestible documents instead of `71`
- a live deployed sync wrote many new `sources` rows and many non-null `source_embedding` values before browser-request reliability became the limiting factor
- latest verified live DB state in this session reached:
  - `714` rows in `sources`
  - `643` rows in `sources` with non-null `source_embedding`
  - `1800` rows in `chunks`
- browser-triggered sync can still outlive the client request, so UI error copy may not reflect real backend progress on long runs

### Verified

- targeted ingestion test passes: `PYTHONPATH=. pytest tests/ingestion/test_readwise.py`
- source embeddings are written only for newly inserted sources in the current sync flow
- live sanity check: the current Readwise token now yields 714 ingestible documents instead of 71 once `html_content` fallback is used

### Completed (three-task subagent trial)

- used subagents to evaluate the first three ordered TODO items instead of updating the project state purely from chat summaries
- verified that most of the old Phase 3 planning artifacts already matched the new `sources.source_embedding` reality
- fixed the remaining stale Phase 3 planning references so the plan no longer drifts back toward chunk-average source vectors or outdated embedding API examples
- made an explicit decision that missing `source_embedding` rows need a dedicated backfill path before broad clustering rollout
- made an explicit decision that missing chunks are a real reliability issue but not the primary blocker for broad clustering rollout

### Verified (subagent findings)

- the one material remaining plan contradiction was inside `.planning/phases/03-clustering-topic-evolution/03-01-PLAN.md`, where the stub still described chunk-average source embeddings
- `.planning/phases/03-clustering-topic-evolution/03-RESEARCH.md` still described `readwise.py` as unchanged even though ingestion now writes `source_embedding`
- `.planning/phases/03-clustering-topic-evolution/03-02-PLAN.md` still used a stale embedding API example
- all three issues were corrected centrally after review

### Completed (source-embedding backfill path)

- added a dedicated ingestion repair helper that finds rows where `sources.source_embedding` is NULL and backfills them from stored `raw_text`
- reused the same whole-source truncation and embedding logic as normal source inserts so old-row repair matches new-row sync behavior
- exposed the repair flow as an explicit `backfill-source-embeddings` CLI command instead of mixing it into normal sync
- added focused ingestion coverage for repairing only NULL source-embedding rows while skipping rows with missing `raw_text`

### Verified

- targeted ingestion tests pass: `PYTHONPATH=. pytest tests/ingestion/test_readwise.py`
- the backfill path updates only rows missing `source_embedding`
- rows without `raw_text` are skipped rather than backfilled with low-trust input
- this task stops before topic assignment or clustering work

### Completed (chat transport wording cleanup)

- updated the main chat backend docstring so `/api/chat` is described as returning one JSON payload instead of SSE
- renamed frontend chat callback and pending-state language so the current request flow is described as full-response JSON, not token streaming
- removed the unused frontend `ChatEvent` SSE type that no longer matches the current `/api/chat` contract
- confirmed the existing chat router test already matches the JSON response shape and did not need behavior changes

### Verified

- focused chat router test passes: `PYTHONPATH=backend:. pytest backend/tests/chat/test_router.py`
- focused frontend lint passes: `cd frontend && npm run lint -- src/components/ChatPanel.tsx src/components/MessageBubble.tsx src/lib/api.ts src/lib/types.ts`
- a repo search now leaves the stale SSE wording in planning/history docs rather than in the active chat execution path

### Next

- next task: implement the next true Phase 3 topic prerequisite after ingestion reliability is settled
- stop before broad topic UI or synthesis work

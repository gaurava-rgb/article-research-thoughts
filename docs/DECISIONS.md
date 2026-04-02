# Decisions

## 2026-03-23

Decision: ship the first durable topic-assignment pass as an explicit `assign-topics` CLI command before wiring it into normal sync.

Why:

- the active task called for source-to-topic assignment mechanics, not broader sync orchestration
- an explicit command makes assignment behavior testable and usable without making every sync depend on new LLM-backed topic creation
- this keeps Phase 3 incremental: durable memberships now, automatic sync assignment later

Consequence:

- backend now has a supported manual path that assigns unassigned sources into `source_topics`
- new topics can be created on demand with LLM naming when centroid matching finds no fit
- normal `sync` behavior remains unchanged until a later task deliberately folds topic assignment into it

## 2026-03-23

Decision: make centroid storage and topic matching the first true Phase 3 topic-structure implementation step, before full assignment orchestration.

Why:

- `sources.source_embedding` coverage and repair are now in acceptable shape, so Phase 3 can move beyond ingestion-only work
- the smallest durable backend slice is to store `topics.centroid_embedding` and expose one consistent matching path against those centroids
- wiring full assignment, topic creation, and sync orchestration in the same step would be a broader rollout than this task called for

Consequence:

- `schema.sql` now includes `topics.centroid_embedding` and a `match_topic` SQL helper
- backend foundation code now covers stored source-vector lookup, centroid recomputation, topic matching, and date-filtered topic source retrieval
- the next task should build assignment mechanics on top of this foundation instead of re-deciding centroid or matching design

## 2026-03-23

Decision: treat browser-visible `/api/sync` results as request-level status, not as authoritative proof that all backend sync work stopped.

Why:

- large Readwise syncs can outlast the browser request lifecycle
- showing every interrupted request as a clean failure makes the product feel less trustworthy than the backend reality
- the smallest honest fix is UI copy and state handling that acknowledges uncertainty without adding background jobs yet

Consequence:

- the sync panel now warns up front that large syncs may outlast one browser request
- interrupted or unresolved sync requests are shown as an uncertain state instead of as a definite backend failure
- this task stops before job queues, worker status endpoints, or deeper sync architecture changes

## 2026-03-23

Decision: make zero-chunk repair a shared sync behavior and do not let CLI sync skip it when a run inserts no new articles.

Why:

- partial-progress ingestion leaves corpus rows that exist in `sources` but are absent from `chunks`
- browser-triggered sync already tried to heal that state, while CLI sync returned early on no-new-article runs
- the smallest reliability improvement is to make both entry points use the same bounded repair pass

Consequence:

- both CLI and UI sync now run the same zero-chunk repair helper after storing articles
- rerunning `second-brain sync` can heal chunk coverage even when the current run is all skips
- this task stops at chunk coverage repair and does not redesign long-running sync UX

## 2026-03-23

Decision: move from GSD-heavy daily execution to a lightweight Cursor-native workflow.

Why:

- lower prompt context was not enough to offset black-box execution
- debugging and UI iteration suffered
- progress needed to stay visible and controllable

Consequence:

- keep durable docs
- keep future specs
- stop using large autonomous phase execution as the default working mode

## 2026-03-23

Decision: use `docs/NOW.md` as the single source of truth for the current task.

Why:

- one-file task focus keeps sessions small and legible
- it prevents accidental spillover into unrelated work

Consequence:

- every meaningful task should define scope, done criteria, and a stop condition there

## 2026-03-23

Decision: separate product truth from implementation sequencing.

Why:

- future phases became too abstract when stored mainly as "phases"
- product intent needs to stay concrete even before implementation begins

Consequence:

- `docs/PROJECT.md` holds end-state product truth
- `docs/ROADMAP.md` holds milestone order
- `docs/SPECS/` holds deep future-phase design

## 2026-03-23

Decision: repair product feel before diving deeper into backend complexity.

Why:

- the current frontend undermines confidence in the system even though the backend base is solid
- UI quality problems are visible immediately and affect every future test cycle

Consequence:

- likely next implementation work should improve first-run UX and app shell quality before or alongside Phase 3

## 2026-03-23

Decision: start Phase 3 with source-level embeddings before topic assignment.

Why:

- topic assignment should operate on whole articles, not only retrieval chunks
- source-level embeddings are a small, durable prerequisite that keeps Phase 3 visible and incremental

Consequence:

- the next task should add source embedding storage and sync-time writes
- clustering, summaries, and topic endpoints should wait until that base exists

## 2026-03-23

Decision: store one whole-source vector on `sources.source_embedding` at insert time during sync.

Why:

- Phase 3 topic work needs a durable article-level representation separate from retrieval chunks
- writing it when a source is first inserted keeps the prerequisite small and idempotent

Consequence:

- new sources receive one source-level embedding during sync
- chunk embeddings remain the retrieval path and are not repurposed for topic assignment

## 2026-03-23

Decision: use Reader API `withHtmlContent=true` and treat `html_content` as the fallback text source when `content` is null.

Why:

- newer Reader documents were present in the API but often returned `content = null`
- direct inspection showed the full article body was still available through `html_content`
- relying on `content` alone incorrectly made the sync appear stale after March 10

Consequence:

- Reader ingestion must request `withHtmlContent=true`
- ingestion should extract plain text from `html_content` before discarding a document as too short
- `summary` is not the primary content source for this sync path

## 2026-03-23

Decision: cap whole-source embedding input to a safe token budget and treat duplicate source inserts as resumable skips.

Why:

- whole-source embeddings can exceed safe embedding-model limits once full Reader HTML text is used
- long-running sync retries can encounter duplicate `readwise_id` inserts after partial progress

Consequence:

- source-level embeddings use truncated whole-source text when necessary, while chunking still uses the regular chunk pipeline
- duplicate insert races on `sources.readwise_id` should not abort the sync
- browser-triggered sync should be treated as operationally resumable even when the UI request is fragile

## 2026-03-23

Decision: treat broad Phase 3 clustering rollout as blocked until missing `sources.source_embedding` rows have an explicit backfill or repair path.

Why:

- the documented verified state still shows a meaningful slice of sources without article-level vectors
- the current clustering direction depends on stored whole-source embeddings as the vector of record
- rerunning normal sync does not automatically repair older existing rows that were inserted before the source-embedding write path existed

Consequence:

- the next smallest backend task should be a dedicated backfill or repair path for `source_embedding`
- broad clustering should not assume whole-corpus coverage until that repair path exists

## 2026-03-23

Decision: treat missing chunks for partially processed rows as a real ingestion-reliability concern, but not a hard blocker for broad Phase 3 clustering rollout.

Why:

- the current Phase 3 topic design depends more directly on `sources.source_embedding` coverage than on perfect chunk coverage
- the browser-triggered sync already has a zero-chunk repair pass, even though CLI and UI sync behavior are still asymmetric
- chunk gaps still matter for retrieval trust and operational consistency, but they are not the most immediate blocker to topic assignment

Consequence:

- chunk repair should remain near the top of the backlog
- source-embedding backfill should come first
- a future sync repair pass should make CLI and UI corpus-healing behavior more consistent

## 2026-03-23

Decision: ship source-embedding repair as an explicit CLI backfill command rather than hiding it inside normal sync.

Why:

- existing sync intentionally skips already inserted sources, so silently folding repair into that path would blur operational behavior
- the smallest safe fix is a targeted command that updates only rows with `source_embedding IS NULL`
- a dedicated command can reuse the exact same whole-source truncation and embedding assumptions as current inserts

Consequence:

- older rows can be repaired with a supported `backfill-source-embeddings` CLI flow
- normal sync behavior stays focused on ingesting new articles
- this task stops at article-level vector repair and does not begin topic assignment work

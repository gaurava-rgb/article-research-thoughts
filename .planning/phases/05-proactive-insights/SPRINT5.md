# Sprint 5 — Proactive Insights + Digests

**Goal:** System surfaces patterns and insights without being asked — weekly digest, proactive "you might find this interesting" nudges, unseen insight badge.
**Phase:** 05
**Status:** Not started — decision needed at session start

---

## Carry-over from Sprint 4 (do first)

| Item | Detail |
|------|--------|
| 147 tweet sources have no chunks | repair-chunks pagination bug is now fixed — safe to re-run |
| Obsidian tweet search | Won't return results until those 147 sources are chunked |

Run this before anything else:
```bash
cd /Users/gauravarora/Documents/Articleresearchthoughts/backend
.venv/bin/python -m second_brain.cli repair-chunks
```

---

## Decision needed at session start

### Option A — Finish data layer first (recommended warm-up, ~30 min)
Run repair-chunks for remaining 147 unchunked sources, verify Obsidian tweet search works end-to-end. No new features — just makes the corpus complete before Phase 5 builds on it.

### Option B — Weekly Digest endpoint
Build `/api/digest` that:
1. Pulls recent saves (last 7 days) from `sources`
2. Runs hybrid search to cluster by theme
3. Returns a structured "what you've been reading" summary
4. Adds a digest card to the UI sidebar

### Option C — Proactive Insights on new chat
On each new conversation, surface a nudge: "3 of your recent saves relate to what you asked last week about AI safety." Requires comparing new conversation topic against recent source embeddings.

**Recommendation:** Option A → Option B. Digest is the highest-value Phase 5 feature and benefits from a complete corpus.

---

## Current system state (as of 2026-04-02)

| Item | State |
|------|-------|
| Sources | 765 |
| Chunks | ~3,389 (post-dedup cleanup) |
| Chunks missing | 147 tweet sources unchunked |
| x.com URLs | 350 sources correctly backfilled |
| SQL search | Full-scan (exact, no ANN approximation) |
| Supabase statement_timeout | 30s |
| Supabase storage | Recovering — was near 500MB free tier limit |
| LLM | meta-llama/llama-3.1-8b-instruct via OpenRouter |

---

## Architectural Concerns

### [CONCERN] Cross-session memory causes slow rot

The current implementation (`chat/memory.py`) embeds every assistant response and injects similar past responses as context into future prompts.

**Problem:** Source articles are ground truth. AI responses are derivatives. Feeding derivatives back as context for future responses creates derivatives-of-derivatives — errors compound, context collapses across conversations, and the AI starts effectively citing itself instead of your actual reading.

Specific failure modes:
- A subtly wrong synthesis from months ago resurfaces and reinforces itself
- An answer correct in one conversation becomes misleading in a different question context
- Your thinking evolves on a topic but old responses keep bleeding in
- The original articles get bypassed — the AI's old summaries become the de facto source

**Recommended fix:** Replace silent context injection with explicit surfacing. Show the user "you asked about this before in conversation X" as a navigable pointer — don't inject the old answer into the prompt. Keep source articles as the only live retrieval context.

**Impact on Phase 5:** Any proactive insights or digest features must be grounded in `sources`/`chunks` only — not past assistant messages.

**Potential approach (2 changes):**

1. **Stop embedding assistant responses** — remove the embedding call in `chat/router.py` Step 5, drop `messages.embedding` column and its IVFFlat index. Assistant responses no longer need to be searchable.

2. **Replace memory injection with a surface pointer** — instead of `search_past_messages` injecting old answers silently into the LLM prompt, query past conversations by topic similarity using the conversation's first *user* message embedding. Return a UI-visible nudge ("you explored this in conversation X") rather than invisible prompt context. Drop the `search_past_messages` SQL function and remove the memory retrieval step from prompt assembly in `chat/conversation.py`.

---

## Progress Log

| Date | What happened |
|------|--------------|
| 2026-04-02 | Sprint 5 executed. Option A (repair-chunks) done. Option B (weekly digest) done. Architectural memory fix done. All 35 tests passing. |
| 2026-04-02 | **Architectural fix**: Removed silent `retrieve_memory_context` injection from LLM prompt in `router.py`. `save_message_with_embedding` → `save_message` (AI responses no longer embedded). `memory.py` refactored: `retrieve_memory_context` (str) → `retrieve_similar_conversations` (list[dict]). |
| 2026-04-02 | **Insights backend**: New `backend/second_brain/ingestion/insights.py` with `generate_digest`, `get_insights`, `mark_seen`. Three new endpoints: `GET /api/insights`, `PATCH /api/insights/{id}/seen`, `POST /api/insights/generate-digest`. |
| 2026-04-02 | **Insights frontend**: `Insight`+`RelatedConversation` types added. `fetchInsights`, `markInsightSeen`, `generateDigest`, `fetchSimilarConversations` added to `api.ts`. `ConvSidebar` now shows insight badge (unseen count) + collapsible insight list with read-on-click. `IngestionPanel` has "Generate Digest" button. `ChatPanel` shows "You explored related topics before" nudge after first message (using `/api/conversations/similar`). |
| 2026-04-02 | **Tests**: `test_memory.py` updated to use `retrieve_similar_conversations`. `test_conversation.py` updated (removed `memory_context` param). `test_router.py` cleaned (removed memory mock). `FakeChunksTable` in `test_readwise.py` fixed with `.range()` support. New `tests/insights/test_insights.py` (6 tests). 35/35 passing. |
| 2026-04-02 | repair-chunks carry-over done: 59 sources repaired, 285 chunks, 1 epub-junk skipped. Fixed embedding crash in `backfill_missing_chunks` (now skips bad sources instead of crashing). Corpus ready for Phase 5. |
| 2026-04-02 | Sprint 5 file created. Carry-over identified. Decision deferred to next session. |
| 2026-04-01 | Cross-session memory concern flagged — see Architectural Concerns above. |

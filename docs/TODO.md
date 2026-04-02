# TODO

This file is the high-level project board for Second Brain.

It answers:

- what is still left to build
- what is currently underway or partially complete
- what is already done
- why each item matters to the product goal

The core product goal remains:

"Help answer what I actually think about X by synthesizing across saved sources, not just retrieving chunks."

## todo

1. Implement a dedicated backfill/repair path for rows where `sources.source_embedding` is still NULL: broad Phase 3 clustering should not roll out across the whole corpus while roughly 10 percent of sources still lack the article-level vector that topic assignment depends on.
2. Decide and implement the smallest remaining ingestion-reliability step after source-embedding backfill is in place: some sources still have partial progress states, and Phase 3 topic work will be more trustworthy if the corpus repair story is clear first.
3. Make long-running sync behavior honest and understandable in the UI: browser-triggered sync can outlive the request, so the product should not imply total failure when backend work may still be progressing.
4. Reconcile old streaming language in code and tests with the current JSON-returning chat implementation: stale SSE wording creates confusion for future debugging and feature work.
5. Implement the next true Phase 3 topic prerequisite after ingestion reliability is settled: the project now needs to move from "article-level embeddings exist" to "articles can be structured into topics."
6. Add topic centroid or matching logic consistent with the current source-level embedding design: Phase 3 depends on comparing whole-source vectors against evolving topic representations.
7. Add topic matching and assignment logic: this is the first real step that turns the corpus from flat retrieval into structured knowledge.
8. Store topic membership in `source_topics`: durable topic relationships are necessary for topic summaries, topic browsing, and later synthesis.
9. Add topic summary generation and regeneration: without summaries, topics exist only as IDs and do not yet become useful product objects.
10. Add temporal topic retrieval support: the system promise includes being able to ask what changed over time, which requires date-aware topic/source access.
11. Add a topics-facing API surface: later synthesis and UI work should not need to reach directly into the database for topic data.
12. Design a dedicated synthesis layer for Phase 4: the current chat path is still one retrieval-plus-prompt flow and is too monolithic for reliable synthesis behavior.
13. Add query-type aware retrieval for synthesis: different questions need different evidence strategies, such as chunk retrieval, topic retrieval, temporal retrieval, or conversation memory.
14. Implement narrative synthesis answers across multiple sources: this is the heart of the product promise and the point where the system stops being only enhanced RAG.
15. Improve citation grounding in synthesis responses: citations need to support claims clearly, not just appear as decorative source cards.
16. Add contradiction detection and surfacing: the product should help the user see disagreements and tensions in the corpus rather than flattening them away.
17. Add better frontend support for synthesis responses: richer answer structure may need stronger UI than the current message-bubble-only layout.
18. Design the background workflow architecture for Phase 5: proactive insights and digests likely need scheduled or asynchronous work rather than chat-time generation.
19. Implement durable insight records beyond the current minimal `insights` table shape if needed: proactive features require provenance, inspectability, and trust.
20. Consider historical topic snapshots or change records: if the product should explain how topics evolved, it may need more than one mutable summary field.
21. Generate periodic digests: this is one of the clearest user-facing signs that the system is becoming a true second brain rather than only reactive chat.
22. Add unseen-insight UI and an insight-reading surface: a badge alone is not enough; the user needs a satisfying place to inspect generated insights.
23. Decide whether to add optional external "AI researched" supplemental sources later: this is a useful extension, but it must stay clearly labeled and separate from the user-owned corpus.
24. Keep docs, tests, and active task state aligned as implementation continues: the new workflow only helps if the written state remains trustworthy.

## in progress

- Lightweight Cursor-native workflow is active: this matters because the project now depends on small, visible task loops instead of opaque phase execution.
- Source-level embedding prerequisite is materially working: this matters because Phase 3 topic logic should operate on article-level vectors, not only retrieval chunks.
- Readwise Reader ingestion now uses `withHtmlContent=true` and falls back to `html_content`: this matters because newer Reader documents were being missed when `content` was null.
- Whole-source embedding input is truncated to a safe token budget: this matters because long articles should not cause source-level embedding writes to fail.
- Duplicate `readwise_id` insert races are treated as resumable skips: this matters because long-running sync retries should not abort the whole pipeline.
- Missing chunks for partially processed rows were assessed as a real reliability issue but not a hard blocker for broad Phase 3 clustering rollout: this matters because clustering depends more directly on `source_embedding` coverage than on perfect chunk coverage, though CLI/UI sync behavior is still asymmetric.

## done

- Phase 1 foundation is complete: ingestion, schema, hybrid retrieval, and provider abstraction exist, which matters because the system already has a usable knowledge-base core.
- Phase 2 chat and memory base is complete: conversations, past-message recall, and the browser chat shell exist, which matters because the product already supports grounded multi-turn interaction.
- Lightweight project docs were created: `CURSORPLAN.md`, `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/NOW.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`, `docs/PLAYBOOK.md`, and future specs now exist, which matters because project memory no longer depends only on chat context.
- Future Phase 4 and Phase 5 intent was written down in dedicated specs: this matters because the long-term product shape is now more concrete and less likely to disappear into vague "later phases."
- The weakest Phase 2 frontend issues were addressed in at least one implementation pass: this matters because the app shell now has a better chance of being usable enough for continued iteration.
- `schema.sql` now includes durable article-level embedding storage on `sources.source_embedding`: this matters because topic work needs one vector per source.
- Sync storage now writes source-level embeddings for newly inserted Reader articles: this matters because future topic assignment depends on article-level vectors already being present at ingestion time.
- The UI-triggered `/api/sync` path now passes the embedding provider through to article storage: this matters because browser-triggered sync should not lag behind the CLI sync path.
- Reader ingestion was fixed to recover text from `html_content` when `content` is null: this matters because many newer saved documents were previously invisible to the pipeline.
- Large source text is capped before embedding: this matters because full-article embeddings should survive realistic document sizes.
- Duplicate insert races are handled as skipped rows instead of hard failures: this matters because long sync runs should degrade gracefully.
- Targeted ingestion and sync-path tests were added around the new source-level embedding behavior: this matters because Phase 3 prerequisites now have some focused regression protection.
- The old GSD Phase 3 plan was reconciled with the current code reality: this matters because future Phase 3 work should consistently reuse `sources.source_embedding` instead of drifting back toward stale chunk-average or second-column assumptions.
- A decision was made that missing `source_embedding` rows require a dedicated backfill path before broad clustering rollout: this matters because topic assignment should not silently exclude a meaningful slice of the corpus.
- A decision was made that chunk repair is useful but not a hard blocker before broad clustering rollout: this matters because the next smallest reliable task should focus on source-embedding coverage first.

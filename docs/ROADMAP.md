# Roadmap

## Principle

This roadmap is strategic, not procedural.

It defines what must become true, but it does not prescribe large autonomous execution chains. Day-to-day work should be driven from `docs/NOW.md`.

## Milestones

### Milestone 1: Reliable Knowledge Base

Status: mostly complete

Goal:

- ingest the Readwise corpus reliably
- retrieve it semantically
- support conversational querying and memory

What must be true:

- ingestion works incrementally
- retrieval is grounded and useful
- conversations persist
- prior chats are resumable

Notes:

- backend foundation is in place
- frontend exists but feels skeletal in use

### Milestone 2: Corpus Structure

Status: next

Goal:

- automatically organize articles into evolving topics

What must be true:

- new articles join topics automatically
- topics update as corpus grows
- topic summaries exist and stay current
- time-aware queries become possible

### Milestone 3: True Synthesis

Status: planned

Goal:

- answer complex questions with narrative synthesis instead of excerpt stitching

What must be true:

- answers combine evidence across multiple sources
- source-grounded claims and model analysis are explicitly separated
- contradictions are surfaced when relevant
- topic and time-aware retrieval inform answers

### Milestone 4: Proactive Insight Surface

Status: planned

Goal:

- generate insights and digests without explicit user prompts

What must be true:

- the system detects patterns and contradictions in the background
- insight records accumulate durably
- weekly or periodic digests summarize what changed
- the UI exposes unseen insights clearly

Notes:

- a future optional extension is on-demand external research, where the system fetches outside articles or documents and stores them with explicit `AI researched` provenance
- this should remain supplementary to the personal corpus, not become the default ingestion path

## Near-Term Priorities

Current priorities, in order:

1. replace GSD-heavy execution with a lighter Cursor workflow
2. fix the weakest Phase 2 UX issues so the app feels usable
3. execute Phase 3 in small visible tasks
4. design Phase 4 as a synthesis layer before implementing it

## Working Rule

If a roadmap item cannot be translated into a small task in `docs/NOW.md`, it is still too big and needs splitting before implementation.

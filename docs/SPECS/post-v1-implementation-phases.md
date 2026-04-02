# Post-v1 Implementation Phases

## Rollback Snapshot

Before starting this plan, the current implementation was snapshotted in git:

- branch: `codex-post-v1-analyst-workbench`
- tag: `snapshot-2026-04-02-pre-analyst-workbench`
- commit: `cdeb6ab`

This gives a clean rollback point before the next implementation wave.

## Working Assumptions

- Readwise remains the only top-of-funnel for now.
- The next iteration should be additive, not a rewrite.
- The product should move from `source -> chunk -> answer` to `source -> entity -> claim -> timeline -> synthesis`.
- Similar-conversation retrieval is optional and non-core.
- Generic recommendations are out of scope; gap-aware follow-up suggestions are in scope.
- The concept map should be a view over stored evidence, not the source of truth.

## Phase Sequence

### Phase 1: Foundation Patch

- goal: make the schema and Readwise ingest ready for structured analysis
- user-visible value: sources become more legible and classifiable instead of being flat article rows
- main outcome: enriched `sources` / `chunks` plus processing provenance
- detail: [06-01-PLAN.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/phases/06-analyst-workbench/06-01-PLAN.md)

### Phase 2: Claims And Evidence

- goal: turn saved reading into extractable analytical primitives
- user-visible value: each source can show entities, claims, and supporting evidence
- main outcome: durable `entities`, `claims`, `claim_evidence`, `claim_lenses`
- detail: [06-02-PLAN.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/phases/06-analyst-workbench/06-02-PLAN.md)

### Phase 3: Dossier And Timeline

- goal: answer "what changed?" and "why is this here?" for a company, product, or market
- user-visible value: entity dossier, timeline, and explainability drilldown
- main outcome: first non-chat analyst surface
- detail: [06-03-PLAN.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/phases/06-analyst-workbench/06-03-PLAN.md)

### Phase 4: Research Gaps And Follow-ups

- goal: suggest what to read next because it improves the map, not because it is merely similar
- user-visible value: coverage gaps, counterpoints, follow-ups, and watch items
- main outcome: evidence-backed suggestion layer
- detail: [06-04-PLAN.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/phases/06-analyst-workbench/06-04-PLAN.md)

### Phase 5: Concept Map And Ripple View

- goal: render an explainable concept map from stored primitives
- user-visible value: annotated map and ripple exploration with source drilldown
- main outcome: evidence-backed graph surface, not opaque LLM visualization
- detail: [06-05-PLAN.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/phases/06-analyst-workbench/06-05-PLAN.md)

## Delivery Principles

- each phase must ship user-visible value, not only backend plumbing
- each phase must leave the existing chat flow functional
- each phase must be testable in isolation
- later phases should reuse phase-2 primitives instead of inventing new parallel structures
- do not add new connectors, a graph database, or autonomous workflows until the phase-3 surface proves the model

## Recommended Start

Start with Phase 1 and Phase 2 only.

That is the minimum slice that turns the system from retrieval-only into analysis-capable without taking on UI or graph complexity too early.

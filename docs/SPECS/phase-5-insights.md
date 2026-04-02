# Phase 5 Spec: Proactive Insights And Digests

## Why This Phase Exists

The product becomes much more valuable when it can notice useful things without waiting for the user to ask the exact right question.

This phase turns the system from reactive chat into an active knowledge companion.

## Product Goal

Generate useful insight objects and digest summaries from the evolving corpus, then surface them in the UI in a way that feels lightweight, trustworthy, and easy to review.

## Core Outputs

### Insight

An insight is a durable record of something the system noticed.

Examples:

- a recurring theme across newly ingested sources
- a contradiction between two author clusters
- a notable change in tone or position within a topic
- a cross-topic connection worth surfacing

### Digest

A digest is a periodic summary of what changed in the corpus.

Examples:

- what was ingested this week
- which topics grew
- what new themes emerged
- what tensions or contradictions appeared

## What Counts As Success

The feature is successful when the user can open the app and quickly learn:

- what changed recently
- what is worth paying attention to
- where the system sees tension or novelty

without needing to explore manually through chat first.

## Architectural Requirement

This phase likely requires background workflow infrastructure.

Do not assume it can be implemented only inside request-time chat routes.

Likely needs:

- scheduled jobs or a lightweight job table
- durable records for insights and digests
- status or timestamps for generation runs
- historical context for topic evolution

## Data Requirements

The current `insights` table is a start, but Phase 5 may need more durable history than one latest-state record per concept.

Possible additions later:

- topic snapshot history
- digest run records
- insight provenance fields
- confidence or status fields
- links from insights to supporting sources or topics

## Generation Triggers

Possible triggers:

- after a sync completes
- on a schedule, such as weekly
- after enough topic changes accumulate

Recommended early strategy:

- weekly digest generation
- lightweight post-sync insight generation for notable changes

## Insight Types

Useful first categories:

- `pattern`
- `contradiction`
- `trend`
- `digest`

These can evolve later, but the UI and data model should assume more than one kind of proactive output.

## Suggested Pipeline

1. identify changed sources and changed topics since last run
2. gather candidate patterns and tensions
3. filter to the most useful outputs
4. generate durable insight records
5. generate digest summary if schedule or threshold says to
6. surface unseen count in UI

## UI Surface

The UI should not bury proactive output inside normal chat history.

Eventually the product should have:

- unseen insight count
- a lightweight insight list or panel
- an easy way to open supporting evidence
- clear marking of what is newly generated

## Relationship To Chat

Insights should enrich chat, but not depend on chat to exist.

Good behavior:

- user sees an insight and opens it
- user clicks into supporting sources or topic pages
- user asks a follow-up in chat with the insight as context

## Optional External Supplementation

A future optional capability is to let the system fetch external news or documents on demand and add them to the corpus as supplemental material.

If implemented, this should follow strict rules:

- every such item must be clearly labeled as `AI researched` or equivalent
- provenance should record source URL, fetch time, and retrieval method
- these items should be easy to filter separately from user-owned corpus material
- synthesis and insights should preserve the distinction between personal corpus evidence and externally fetched evidence

This is not a current milestone requirement. It is a parked extension that may become useful once the core insight and digest flow is stable.

## Failure Modes To Avoid

- noisy low-value insight spam
- fake novelty based on weak retrieval artifacts
- digests that merely restate titles of new articles
- hidden background work that is impossible to inspect
- UI badge without a satisfying insight surface behind it

## Minimum Implementation Mindset

The first version should optimize for trust and usefulness, not coverage.

Better:

- a small number of clearly useful insights

Worse:

- lots of weak observations that train the user to ignore the feature

The first implementation should make insight generation inspectable and reversible, even if it is simple.

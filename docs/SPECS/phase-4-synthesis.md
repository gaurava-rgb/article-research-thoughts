# Phase 4 Spec: Synthesis Engine

## Why This Phase Exists

The project stops being "smart RAG chat" and starts becoming a true second-brain product only when answers are synthesized across the corpus instead of being assembled from top chunks.

## Product Goal

When the user asks a complex question, the system should produce a narrative answer that:

- integrates evidence across multiple sources
- separates source-grounded claims from model interpretation
- cites relevant sources
- surfaces contradictions and tensions
- supports time-aware comparisons when relevant

## What Counts As Success

A good answer:

- does not read like retrieved excerpts pasted together
- does not hide uncertainty
- does not collapse disagreement into one bland statement
- does show what came from the corpus versus what is model synthesis

## Query Types To Support

### Direct Synthesis

Examples:

- What do I think about AI safety?
- What themes show up across my reading on attention?

Needs:

- multi-source retrieval
- topic grouping
- evidence aggregation

### Comparative Synthesis

Examples:

- How do these authors disagree on remote work?
- What changed in my corpus about AI agents between Q3 and Q4?

Needs:

- topic-aware retrieval
- time-aware retrieval
- contradiction detection
- comparison framing

### Recall Plus Synthesis

Examples:

- We talked about this before. What was the thread?
- How does this connect to the March conversation?

Needs:

- conversation memory
- source retrieval
- synthesis across both

## Required Answer Shape

The answer format should stay explicit.

Minimum structure:

- `[FROM YOUR SOURCES]`
- `[ANALYSIS]`

Possible future additions:

- `[CONTRADICTIONS]`
- `[WHAT CHANGED]`

The exact UI styling can evolve, but the conceptual boundaries should remain visible.

## Retrieval Strategy

Phase 4 should not rely only on top-k chunk similarity.

Likely retrieval modes:

- chunk retrieval for direct evidence
- topic retrieval for thematic coverage
- temporal retrieval for "what changed" questions
- memory retrieval for prior conversation continuity

The system should choose retrieval strategy based on question type rather than always doing the same thing.

## Suggested Pipeline

1. classify the question
2. choose retrieval strategy
3. collect evidence from sources, topics, dates, and memory
4. cluster or group evidence into claims
5. identify contradictions or tensions
6. compose answer with explicit evidence boundaries
7. attach citations

## Architecture Implication

This phase likely needs a synthesis layer between the API route and the LLM call.

Avoid:

- endlessly growing `router.py`
- one giant prompt that tries to handle every question type

Prefer:

- a synthesis service or module
- query-type aware retrieval orchestration
- explicit answer-construction logic

## Contradiction Handling

Contradiction handling does not need perfect formal logic.

It does need:

- clear recognition when sources meaningfully disagree
- honest phrasing
- citation of both sides
- separation between contradiction found in sources and model interpretation of that contradiction

## UX Implication

The frontend should support synthesis as a product surface, not just message bubbles.

Eventually useful additions may include:

- clearer section styling
- better citation browsing
- topic-aware context display
- expandable evidence groupings

## Failure Modes To Avoid

- excerpt soup presented as synthesis
- citations that are present but not meaningfully tied to claims
- contradictions being smoothed over into false agreement
- huge prompts that become hard to debug
- answer quality depending too heavily on whichever chunks ranked top-5

## Minimum Implementation Mindset

The first Phase 4 version does not need to solve every query type perfectly.

It does need to establish a new architecture:

- retrieval mode selection
- evidence grouping
- explicit synthesis composition

That architectural step matters more than chasing polish in a single prompt.

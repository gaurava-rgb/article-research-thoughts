# Architecture

## Current Shape

The current application is a monorepo-style project with:

- `backend/`: Python package for ingestion, retrieval, chat, providers, and CLI
- `frontend/`: Next.js chat UI
- `api/index.py`: Vercel-friendly FastAPI entrypoint
- `schema.sql`: database schema and SQL functions

## Current Runtime Model

### Ingestion

Current ingestion flow:

1. fetch from Readwise
2. upsert articles into `sources`
3. chunk article text
4. embed chunks
5. store chunks in `chunks`

Current status:

- implemented for Readwise
- incremental
- chunk-and-embed path exists
- topic assignment is planned but not yet wired in

### Retrieval

Current retrieval is hybrid:

- vector similarity over chunk embeddings
- PostgreSQL full-text search
- weighted in SQL

This is a good foundation for a personal corpus because direct terms and semantic similarity both matter.

### Chat

Current chat flow is mostly:

1. retrieve top chunks
2. retrieve semantically similar past assistant messages
3. build one prompt with sources, memory, and recent history
4. call the LLM once
5. persist the assistant response and its embedding

This works for Phase 2, but it is still architecturally close to enhanced RAG rather than a true synthesis engine.

### Frontend

The frontend currently provides:

- chat panel
- message rendering with source cards
- conversation sidebar
- ingestion panel

Current weakness:

- the UI satisfies requirements better than it satisfies product feel
- several states feel skeletal
- interaction quality is behind backend correctness

## Architectural Strengths

- clear separation between ingestion, retrieval, chat, and provider layers
- swappable LLM and embedding providers
- schema already includes future nouns: `topics`, `source_topics`, `insights`
- hybrid retrieval is already in place
- conversations and message persistence already exist

## Architectural Limits

### Limit 1: Chat path is too monolithic for later synthesis

Phase 4 likely should not remain "one route, one retrieval call, one giant prompt."

Future synthesis will probably need:

- query classification
- topic-aware retrieval
- temporal retrieval
- contradiction gathering
- evidence grouping
- response composition

This suggests a future synthesis layer or service between router and LLM.

### Limit 2: Topic state is not enough on its own for evolution history

If the product needs to answer how a topic evolved, a single mutable topic summary may not be enough.

Likely future needs:

- topic summary snapshots
- topic update events
- digestable history of topic changes

### Limit 3: Proactive insights need background execution

Phase 5 should not depend only on request-time chat routes.

Likely future needs:

- scheduled jobs or a job table
- asynchronous insight generation
- durable insight records and status
- digest generation outside chat request flow

### Limit 4: Frontend needs a stronger app-shell mentality

The current frontend behaves more like a collection of Phase 2 components than a cohesive product shell.

Future frontend work should treat:

- first-run states
- loading states
- conversation freshness
- topic surfaces
- insight surfaces

as core architecture concerns, not polish-only concerns.

## What Phase 3 Should Add

Phase 3 should add structure to the corpus:

- source-level embeddings
- topic matching and assignment
- evolving topic summaries
- topic listing endpoint
- date-aware topic retrieval

This is compatible with the current architecture.

## What Phase 4 Should Add

Phase 4 should add a synthesis layer, not just a larger prompt.

Preferred future flow:

1. classify user question
2. choose retrieval mode
3. gather evidence from sources, topics, and memory
4. detect conflicts and tensions
5. compose structured answer
6. return citations and explanation boundaries

## What Phase 5 Should Add

Phase 5 should add background workflow architecture:

- insight generation jobs
- digest generation jobs
- historical change tracking
- UI surfaces for unseen insights and recent digests

## Current Summary

The current architecture is a solid base for:

- ingestion
- hybrid retrieval
- chat memory

It is mostly ready for Phase 3.

It needs architectural expansion, not just feature additions, for:

- Phase 4 synthesis
- Phase 5 proactive workflows

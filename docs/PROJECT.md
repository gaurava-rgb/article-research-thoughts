# Project

## Name

Second Brain

## One-Liner

A personal knowledge system that turns saved reading into a thinking partner, not just a searchable archive.

## Core Promise

The product should help answer:

"What do I actually think about X based on what I have read?"

That is different from ordinary RAG. The end state is not "retrieve matching chunks and answer." The end state is synthesis, continuity, and proactive insight.

## User

One primary user: the owner of the corpus.

This is a personal tool, not a multi-user SaaS product.

## Product Scope

The system ingests articles from Readwise, stores them in a structured corpus, supports conversational querying, remembers past discussions, organizes material into evolving topics, and eventually produces proactive insights.

## What Success Looks Like

The product is successful when the user can:

- ingest saved reading reliably
- ask a question and get a grounded, useful answer
- continue prior lines of thought across sessions
- see how ideas cluster and evolve over time
- receive synthesis that is better than plain retrieval
- receive proactive insights without needing to ask first

## End-State Capabilities

### Corpus Ingestion

- Readwise ingestion is reliable and incremental.
- Articles are stored with metadata, raw text, chunks, and embeddings.
- Additional sources may come later, but Readwise remains the primary source of truth for now.
- A future optional capability is on-demand external research, where the system fetches relevant articles or documents to supplement the corpus and stores them with explicit provenance such as `AI researched`.

### Retrieval

- Retrieval is semantic, not keyword-only.
- The system uses hybrid retrieval so direct terms and conceptual similarity both matter.
- Retrieval can respect time windows when the user asks temporal questions.

### Conversational Memory

- The user can carry on multi-turn chats.
- Past conversations are available and resumable.
- Relevant prior assistant messages can be recalled across sessions when the current question overlaps with past discussion.

### Topic Structure

- New articles are automatically assigned to topics.
- Topics are not manual tags; they are computed structures over the corpus.
- Topic summaries evolve as new articles join.
- Publication dates matter because the user should be able to ask how thinking changed over time.

### Synthesis Engine

The answer layer should move beyond chunk stitching.

It must:

- answer with narrative synthesis rather than excerpt lists
- separate source-grounded material from model analysis
- cite specific supporting sources
- surface contradictions when sources disagree
- support time-aware questions across topics and periods

### Proactive Insights

The system should eventually generate useful output without an explicit prompt.

It must:

- detect patterns across newly ingested material
- detect contradictions or tensions between sources
- produce periodic digest-style summaries
- expose insights in the UI as a distinct surface, not only inside chat replies

## Non-Goals

- multi-user support
- manual tagging workflows
- real-time collaboration
- mobile-first design
- Notion import as a primary ingestion path

## Future Optional Capability

### AI-Researched Supplemental Sources

The system may eventually support fetching external material on demand to supplement the personal corpus.

This should be treated as a supplement, not a replacement for the user's owned corpus.

Requirements for this capability:

- fetched material must be explicitly labeled as AI-researched or externally sourced
- provenance should include source URL, retrieval time, and retrieval method
- retrieval should be user-invoked or clearly policy-gated, not silently mixed into the core corpus
- answers should preserve the distinction between user-owned sources and externally fetched material

This is parked as a future option, not part of the current implementation scope.

## UX Principles

- The app should feel trustworthy before it feels clever.
- Responses should be honest about what comes from sources versus model interpretation.
- UI should never mark placeholder behavior as complete functionality.
- First-run and loading states must feel intentional, not skeletal.
- Product feel matters as much as requirement coverage for the frontend.

## Technical Constraints

- Backend: Python + FastAPI
- Database: Supabase + PostgreSQL + pgvector
- Frontend: Next.js
- LLM and embedding providers must remain swappable via config
- Personal budget and context budget both matter, so workflows should stay lean

## Current Product Truth

Today the implemented system is best described as:

"enhanced RAG chat with conversation memory"

That is a valid base, but it is not yet the full second-brain experience. The biggest remaining leaps are:

- Phase 3: structure the corpus into evolving topics
- Phase 4: add real synthesis behavior instead of one-shot retrieval-plus-answer
- Phase 5: add background insight generation and digest workflows

## Risks To Watch

- UI can look complete in requirements while feeling unfinished in use.
- Future phases can become vague if only tracked as abstract milestones.
- A single monolithic chat route may become brittle as synthesis complexity grows.
- Proactive insight features will likely require background jobs and historical state, not just request-time logic.

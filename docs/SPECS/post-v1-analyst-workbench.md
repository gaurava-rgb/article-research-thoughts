# Post-v1 Analyst Workbench Schema

## Verdict

Yes, this can be added on top of the current implementation.

The current system is still a viable base because:

- `sources` already gives you one durable row per ingested artifact
- `chunks` already gives you retrieval units and embeddings
- `conversations` and `messages` are still fine as a UI/chat layer
- `topics` can remain as a lightweight browse layer

What is missing is not storage for text. What is missing is storage for analysis.

The product should move from:

- `source -> chunk -> answer`

to:

- `source -> entity -> claim -> timeline -> synthesis`

## What To Keep

- Keep `sources`, but generalize it beyond Readwise.
- Keep `chunks`, but add structure so they can represent transcript turns, thread posts, sections, and evidence spans.
- Keep `conversations` and `messages`.
- Keep `topics` and `source_topics`, but downgrade them from "main structure" to "optional browse/navigation structure".
- Keep `insights`, but make them evidence-backed instead of free-floating prose blobs.

## Readwise-First Is Fine

If Readwise remains the only top-of-funnel for the near term, that is not a problem.

You do not need to build multiple ingest connectors first.

What still matters is that one Readwise-saved source can be many different analytical shapes:

- a reported article
- a strategy essay
- a tweet thread
- a transcript
- a filing excerpt
- your own note/highlight layer

So the schema should still distinguish:

- `source_type`: likely still mostly `readwise`
- `kind`: article, thread, transcript, note, earnings_call
- `tier`: primary, reporting, analysis, social, personal
- `metadata`: flexible source-specific fields carried through from Readwise or later enrichments

If you want the minimal version first, you can keep `readwise_id` as the operational ingress identity for now and delay any real multi-connector work.

## What To Patch

### 1. Generalize `sources`

The current table is too Readwise-specific because `readwise_id` is the primary external identity and is `NOT NULL`.

Patch direction:

- keep the table name `sources` for now
- keep `id` stable so the rest of the app still works
- add generic identity and metadata columns
- make `readwise_id` a legacy transition field, not the universal identity

### 2. Generalize `chunks`

The current `chunks` table is retrieval-oriented only.

Patch direction:

- keep it as the retrieval/evidence table
- add structural metadata so a chunk can also represent:
  - a podcast speaker turn
  - a tweet/thread post slice
  - an earnings-call prepared-remarks block
  - a Q&A response
  - a PDF page span

### 3. Add analysis tables

This is the real missing layer.

Add:

- `entities`
- `entity_aliases`
- `entity_relationships`
- `source_entities`
- `processing_runs`
- `claims`
- `claim_evidence`
- `claim_links`
- `lenses`
- `claim_lenses`
- `insight_claims`
- `insight_entities`

These tables make timeline and ripple analysis possible without forcing the LLM to reconstruct structure from chunks every time.

`entity_relationships` matters for portfolio and ecosystem questions such as:

- Google owns YouTube
- YouTube competes with TikTok
- Google Cloud participates in the cloud infrastructure market
- Anthropic depends on AWS
- Spotify aggregates creators and listeners

## What Is Stable vs Flexible

The schema is meant to have a stable spine and flexible vocabularies.

Stable spine:

- `sources`
- `chunks`
- `entities`
- `entity_relationships`
- `claims`
- `claim_evidence`
- `claim_links`
- `lenses`
- `insights`

Flexible vocabularies:

- `entity_type`
- `relation_type`
- `claim_type`
- `modality`
- `stance`
- `role`
- `lens`
- `metadata`

Those are intentionally modeled with `TEXT` and `JSONB`, not rigid enums.

That means the list is not set in stone.

You can start with a narrow controlled vocabulary, learn from real usage, and then:

- add new lens types
- add new claim types
- split an overloaded relation into two clearer relations
- promote a frequently used metadata field into a real column later

This is the right tradeoff for your use case because the analytical language will evolve as you read more.

## Modeling Products, Markets, Competitors, And Indicators

Do not over-normalize this on day one.

For the first useful version:

- products are `entities`
- companies are `entities`
- markets are `entities`
- people are `entities`
- competitors are expressed through `entity_relationships`
- leading indicators and lagging indicators are expressed as `claims` linked by `claim_links`

Examples:

- `Google -> owns -> YouTube`
- `YouTube -> competes_with -> TikTok`
- `YouTube -> participates_in -> online_video_ad_market`
- `Claim: creator trust brokers accelerate adoption`
- `Claim: creator trust brokers accelerate adoption -> leads_to -> AI distribution through creator channels`
- `Claim: AI distribution through creator channels -> amplifies -> YouTube ecosystem power`

This is enough to answer a lot of the "magic hat" questions without prematurely adding separate `markets`, `products`, `competitors`, or `indicators` tables.

Only add dedicated tables for those if the query load proves they need richer first-class behavior.

## What To Stop Treating As Core

### `topics` / `source_topics`

These are still useful, but they should no longer be the primary answer to structure.

Why:

- auto-named centroid clusters are useful for broad similarity
- they are weak at chronology
- they are weak at "what changed"
- they are weak at "who said what"

Keep them as a secondary navigation surface.

### message embeddings as "memory"

The current design already moved in the right direction by showing similar past conversations in the UI instead of injecting them into the model prompt.

Keep that lightweight UI nudge.

Do not make it the center of the analyst workflow.

### the current `insights.body`-only model

The current `insights` table is too thin for a serious analyst product.

Keep the table, but only as the top-level record.

The actual support should come from linked claims and entities.

## What Not To Add Yet

These are tempting, but they are not the first move:

- a new `artifacts` table replacing `sources`
- a graph database
- topic snapshot history
- fully normalized organization/person/company relationship taxonomies
- autonomous background agents for everything

Why not:

- the current relational shape is still good enough
- replacing `sources` with `artifacts` immediately creates migration churn without unlocking the first useful analyst workflows
- claim extraction and claim-linking are the higher-leverage addition

## Exact Additive Schema

See:

- [post-v1-analyst-workbench.sql](/Users/gauravarora/Documents/Articleresearchthoughts/docs/SPECS/post-v1-analyst-workbench.sql)

That SQL is intentionally additive:

- it preserves `sources.id`
- it preserves `chunks.source_id`
- it preserves current chat and retrieval paths
- it introduces structured analysis storage beside the current v1 system

## Why This Is Patchable

The current implementation claims Phase 4 and Phase 5 are complete in planning state, but the live code is still much narrower than the analyst-workbench target.

The planning files say:

- Phase 4 complete: [.planning/ROADMAP.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/ROADMAP.md#L16)
- Phase 5 complete: [.planning/ROADMAP.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/ROADMAP.md#L17)
- State marks all phases complete: [.planning/STATE.md](/Users/gauravarora/Documents/Articleresearchthoughts/.planning/STATE.md#L45)

But the actual code still behaves like:

- one generic hybrid retrieval call: [router.py](/Users/gauravarora/Documents/Articleresearchthoughts/backend/second_brain/chat/router.py#L65)
- one prompt assembly path: [router.py](/Users/gauravarora/Documents/Articleresearchthoughts/backend/second_brain/chat/router.py#L87)
- one completion call: [router.py](/Users/gauravarora/Documents/Articleresearchthoughts/backend/second_brain/chat/router.py#L104)
- digest generation from recent source titles grouped by topic: [insights.py](/Users/gauravarora/Documents/Articleresearchthoughts/backend/second_brain/ingestion/insights.py#L19)
- topic assignment via centroid matching and LLM naming: [clustering.py](/Users/gauravarora/Documents/Articleresearchthoughts/backend/second_brain/ingestion/clustering.py#L87)

That means you do not need a rewrite. You need a new middle layer.

## Recommended Migration Order

### Step 1

Apply the `sources` and `chunks` patches first.

Goal:

- mixed-source ingestion becomes possible without breaking current Readwise sync

### Step 2

Add `entities`, `entity_relationships`, `claims`, and `claim_evidence`.

Goal:

- one source can produce structured analytical records

### Step 3

Add `claim_links` and `claim_lenses`.

Goal:

- "what changed", "what contradicts", and "what ripple does this create" become queryable

### Step 4

Patch `insights` to point at claims/entities.

Goal:

- insights become inspectable and defensible instead of only generative summaries

### Step 5

Only after the schema exists, build:

- company/entity pages
- timeline view
- ripple view
- mixed-source ingestion adapters

## First Product Surface To Build

If you want the first non-chat surface that proves this schema matters, build:

- an entity page
- a chronological claim timeline
- a "what changed recently" summary for that entity

That gets you much closer to the Stratechery-style workflow than improving generic chat prompts.

## The Right Mind Map

What you are describing is not a generic LLM mind map.

It is an annotated concept map backed by evidence.

That means:

- each bubble should map to a real stored object such as an entity, claim, market, product, or synthesized insight
- each connection should map to a real stored relation such as `owns`, `competes_with`, `depends_on`, `leads_to`, `amplifies`, or `constrains`
- each bubble and edge should be explainable with source-backed evidence

So the product surface is not:

- "generate a pretty graph from all my reading"

It is:

- "render a graph from stored analytical primitives, then let me click through to why each node and edge exists"

This is the crucial difference from an opaque NotebookLM-style map:

- the map is a view, not the source of truth
- the source of truth is claims, entities, links, and evidence
- every node can show supporting sources, contradictory sources, and confidence
- every edge can show what text justified the connection

Topics may still help as one layout or grouping mechanism, but they should not be the main semantic structure of the map.

The better grouping anchors are usually:

- entity
- market
- product
- lens
- thesis
- leading indicator
- lagging outcome

If built this way, the "Jarvis" version of the product is much more realistic:

- ingest sources
- extract analytical primitives
- link them
- render timelines, dossiers, and concept maps from the same underlying structure

Then when a bubble appears, the user can ask:

- why is this here?
- what evidence supports it?
- what other claims does it connect to?
- what changed recently?
- what contradicts it?

That is the difference between a nice visualization and an analyst system.

## AI Suggestions And Augmentation

Yes, this is relevant.

But the right version is not:

- "you may also like this article"

The right version is:

- "this looks relevant because it fills a gap, validates a claim, adds a primary source, adds a counterpoint, or extends a ripple"

That means the suggestion engine should be thesis-aware and evidence-aware.

Good suggestion types:

- primary-source gap
- competitor context
- historical analog
- contradiction / skeptical counterview
- recent update on a watched entity
- downstream ripple follow-up
- missing market context

Examples:

- you read three opinion pieces about OpenAI monetization but no primary source, so the system suggests the latest earnings-style remarks, pricing page changes, or partner announcements
- you read a thesis about AI trust networks, so the system suggests YouTube, WhatsApp, creator-economy, or sovereign-AI sources that either support or pressure-test it
- you read about Google AI distribution, so the system suggests adjacent product or competitor evidence from YouTube, Workspace, Android, Meta, Apple, or regulators

Because Readwise is still your top funnel, the first useful version does not need auto-ingestion.

It can simply surface:

- why this suggestion exists
- what entity / claim / thesis triggered it
- what kind of gap it fills
- a suggested query, URL, or source to look for

Then you decide whether to read and save it into Readwise.

### Lean Implementation

Do not build a full recommendation system first.

Start by reusing `insights` for analyst-facing suggestions such as:

- `coverage_gap`
- `follow_up`
- `counterpoint`
- `watch`

Each suggestion should link back to supporting entities and claims the same way other insights do.

Only add a dedicated `research_suggestions` or `research_queue` table later if you need workflow state such as:

- accepted
- dismissed
- snoozed
- saved_to_readwise
- expired

This keeps the first implementation small while still making the system meaningfully more useful.

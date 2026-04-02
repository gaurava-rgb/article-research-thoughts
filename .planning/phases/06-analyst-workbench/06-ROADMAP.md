# Phase 6 Roadmap: Analyst Workbench

## Objective

Build the post-v1 analyst layer on top of the current implementation without rewriting the existing app.

The new core should be:

- `source`
- `chunk`
- `entity`
- `entity_relationship`
- `claim`
- `claim_evidence`
- `claim_link`
- `insight`

The end state is:

- the user can inspect what the system believes
- each belief can point back to sources and evidence
- the system can answer change-over-time and ripple questions
- the system can suggest missing reading that improves the map

## Ordered Phases

1. Foundation patch
2. Claims and evidence extraction
3. Entity dossier and timeline
4. Research gaps and follow-ups
5. Concept map and ripple view

## Dependency Rule

- phase 2 depends on phase 1
- phase 3 depends on phase 2
- phase 4 depends on phase 2 and is stronger after phase 3
- phase 5 depends on phase 2 and phase 3

## Non-Goals For This Roadmap

- replacing Readwise as the ingestion funnel
- moving to a graph database
- rebuilding the whole chat system
- building a generic recommendation engine
- treating topic clustering as the main structure of the system

## Success Criteria

- a saved source can produce inspectable analytical primitives
- an entity page can show what changed and why
- a suggestion can explain why it exists
- a map node or edge can always answer "why is this here?"

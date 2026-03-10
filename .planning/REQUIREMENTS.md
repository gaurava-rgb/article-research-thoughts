# Requirements: Second Brain — Personal Knowledge System

**Defined:** 2026-03-10
**Core Value:** The system must answer "what do I actually think about X?" by synthesizing across all saved sources — not just retrieve matching text chunks.

## v1 Requirements

### Ingestion

- [x] **ING-01**: User can trigger Readwise Reader sync that imports all articles via READWISE_TOKEN (with correct pagination — no missing articles)
- [x] **ING-02**: Each article is stored with full metadata: title, author, URL, published_at, ingested_at, source_type
- [x] **ING-03**: Articles are chunked into semantic segments (~500 tokens with overlap) and stored as chunks
- [x] **ING-04**: Each chunk has an embedding generated and stored in pgvector
- [x] **ING-05**: Incremental sync — re-running ingestion only processes new/updated articles, not the full corpus

### Retrieval

- [x] **RET-01**: User can search knowledge base semantically (meaning-based, not just keyword matching)
- [x] **RET-02**: Search combines vector similarity + full-text keyword search (hybrid search)
- [x] **RET-03**: User can filter search by time range ("articles from last 3 months", "before 2025")
- [x] **RET-04**: Search results return source metadata (title, author, URL) alongside matched content

### Structuring

- [ ] **STR-01**: New articles are automatically assigned to topics (clusters) on ingestion — no manual tagging required
- [ ] **STR-02**: Topic summaries are automatically rewritten when new articles join a topic
- [ ] **STR-03**: System tracks publication dates to enable temporal reasoning across topics

### Synthesis

- [ ] **SYN-01**: User can ask a question and receive a narrative response that synthesizes across multiple sources (not just excerpts)
- [ ] **SYN-02**: Every response clearly marks [FROM YOUR SOURCES] vs [LLM ANALYSIS] sections
- [ ] **SYN-03**: Every response cites specific articles with clickable links
- [ ] **SYN-04**: System detects contradictions between sources and surfaces them when relevant

### Chat & Memory

- [x] **CHAT-01**: User can have multi-turn conversations — follow-up questions reference prior turns in the same session
- [x] **CHAT-02**: Past conversations are stored and listed in a sidebar
- [x] **CHAT-03**: User can load and continue a past conversation
- [x] **CHAT-04**: Cross-session memory — system recalls relevant past conversations when answering new questions ("remember when we discussed X?")

### Workflows

- [ ] **WORK-01**: System generates a weekly digest summarizing new sources ingested, topic evolution, and emerging themes
- [ ] **WORK-02**: System proactively detects patterns across recent ingestions and stores them as insights
- [ ] **WORK-03**: User sees unseen insight count ("3 new insights") in the chat UI

### Frontend

- [x] **UI-01**: Chat interface with message bubbles and markdown rendering
- [x] **UI-02**: Source citations rendered as expandable cards (click to see original article)
- [x] **UI-03**: Visual distinction between [FROM SOURCES] and [ANALYSIS] content (different styling)
- [x] **UI-04**: Conversation sidebar showing past chats
- [x] **UI-05**: Source ingestion panel — paste URL or trigger Readwise sync
- [ ] **UI-06**: Insight notification indicator in UI
- [x] **UI-07**: Frontend deployed to Vercel

### Infrastructure

- [x] **INFRA-01**: LLM provider is swappable via config.yaml (start with Claude Sonnet via OpenRouter)
- [x] **INFRA-02**: Embedding provider is swappable via config.yaml (start with OpenRouter embeddings)
- [x] **INFRA-03**: Full database schema in schema.sql covering all tables from day one (sources, chunks, topics, source_topics, conversations, messages, insights)

## v2 Requirements

### Extended Ingestion

- **ING-V2-01**: Support PDF upload as ingestion source
- **ING-V2-02**: Support YouTube transcript ingestion
- **ING-V2-03**: Support manual text/note ingestion
- **ING-V2-04**: RSS feed monitoring

### Advanced Synthesis

- **SYN-V2-01**: "Debate mode" — system steelmans opposing arguments from saved sources
- **SYN-V2-02**: Idea generation from cross-topic pattern analysis
- **SYN-V2-03**: Belief tracking — "what do I currently believe about X based on my reading?"

### Local Inference

- **INFRA-V2-01**: Local embedding provider (sentence-transformers) for zero embedding cost
- **INFRA-V2-02**: Local LLM provider (Ollama) for offline use

## Out of Scope

| Feature | Reason |
|---------|--------|
| Notion import | Readwise is source of truth; Notion was a failed workaround |
| Mobile app | Web-first; mobile is a future milestone |
| Multi-user support | Personal tool only |
| Manual tagging | Auto-clustering replaces it |
| Real-time collaboration | Out of scope for personal tool |
| Email notifications | Not in core workflow; possible v2 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ING-01 | Phase 1 | Complete |
| ING-02 | Phase 1 | Complete |
| ING-03 | Phase 1 | Complete |
| ING-04 | Phase 1 | Complete |
| ING-05 | Phase 1 | Complete |
| RET-01 | Phase 1 | Complete |
| RET-02 | Phase 1 | Complete |
| RET-03 | Phase 1 | Complete |
| RET-04 | Phase 1 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| UI-01 | Phase 2 | Complete |
| UI-02 | Phase 2 | Complete |
| UI-03 | Phase 2 | Complete |
| UI-04 | Phase 2 | Complete |
| UI-05 | Phase 2 | Complete |
| UI-07 | Phase 2 | Complete |
| CHAT-01 | Phase 2 | Complete |
| CHAT-02 | Phase 2 | Complete |
| CHAT-03 | Phase 2 | Complete |
| CHAT-04 | Phase 2 | Complete |
| STR-01 | Phase 3 | Pending |
| STR-02 | Phase 3 | Pending |
| STR-03 | Phase 3 | Pending |
| SYN-01 | Phase 4 | Pending |
| SYN-02 | Phase 4 | Pending |
| SYN-03 | Phase 4 | Pending |
| SYN-04 | Phase 4 | Pending |
| WORK-01 | Phase 5 | Pending |
| WORK-02 | Phase 5 | Pending |
| WORK-03 | Phase 5 | Pending |
| UI-06 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after roadmap creation — all 33 requirements mapped*

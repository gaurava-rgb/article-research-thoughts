-- =============================================================================
-- Second Brain — Full Database Schema
-- Apply once to Supabase: psql $DATABASE_URL -f schema.sql
-- =============================================================================

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 1. sources: one row per saved source artifact
--    `readwise_id` remains for backward compatibility with existing rows.
-- =============================================================================
CREATE TABLE sources (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  readwise_id  TEXT        UNIQUE,                   -- legacy Readwise identifier
  external_id  TEXT,
  title        TEXT        NOT NULL,
  author       TEXT,
  url          TEXT,
  source_type  TEXT        NOT NULL DEFAULT 'readwise',
  kind         TEXT        NOT NULL DEFAULT 'article',
  tier         TEXT        NOT NULL DEFAULT 'analysis',
  publisher    TEXT,
  published_at TIMESTAMPTZ,
  remote_updated_at TIMESTAMPTZ,
  parent_source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
  thread_key   TEXT,
  language     TEXT        NOT NULL DEFAULT 'en',
  ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata     JSONB       NOT NULL DEFAULT '{}'::jsonb,
  checksum     TEXT,
  raw_text     TEXT,                                 -- full article text for full-text search
  source_embedding vector(1536)                      -- one whole-source vector for topic work
);

CREATE UNIQUE INDEX sources_source_type_external_id_idx
  ON sources (source_type, external_id)
  WHERE external_id IS NOT NULL;

CREATE INDEX sources_kind_idx
  ON sources (kind);

CREATE INDEX sources_tier_idx
  ON sources (tier);

CREATE INDEX sources_published_at_idx
  ON sources (published_at DESC);

CREATE INDEX sources_parent_source_id_idx
  ON sources (parent_source_id);

CREATE INDEX sources_thread_key_idx
  ON sources (thread_key);

CREATE INDEX sources_publisher_idx
  ON sources (publisher);

CREATE INDEX sources_metadata_gin_idx
  ON sources USING gin (metadata);

-- =============================================================================
-- 2. topics: auto-assigned clusters (populated in Phase 3 — Clustering)
--    These are not user-defined tags; they are computed from embeddings.
-- =============================================================================
CREATE TABLE topics (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT        NOT NULL,
  summary    TEXT,
  centroid_embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 3. source_topics: many-to-many join between sources and topics
--    One source can belong to multiple topics; one topic has many sources.
-- =============================================================================
CREATE TABLE source_topics (
  source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  topic_id  UUID NOT NULL REFERENCES topics(id)  ON DELETE CASCADE,
  PRIMARY KEY (source_id, topic_id)
);

-- =============================================================================
-- 4. chunks: semantic segments of each source article
--    Each source is split into ~500-token overlapping chunks for retrieval.
--    The embedding column stores the vector representation for similarity search.
-- =============================================================================
CREATE TABLE chunks (
  id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id   UUID    NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,           -- position of this chunk within its source (0-based)
  kind        TEXT    NOT NULL DEFAULT 'chunk',
  section_label TEXT,
  speaker     TEXT,
  page_number INTEGER,
  start_char  INTEGER,
  end_char    INTEGER,
  content     TEXT    NOT NULL,
  token_count INTEGER,
  embedding   vector(1536),              -- text-embedding-3-small = 1536 dimensions
  metadata    JSONB   NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX chunks_source_id_chunk_index_idx
  ON chunks (source_id, chunk_index);

CREATE INDEX chunks_kind_idx
  ON chunks (kind);

CREATE INDEX chunks_speaker_idx
  ON chunks (speaker);

CREATE INDEX chunks_section_label_idx
  ON chunks (section_label);

CREATE INDEX chunks_metadata_gin_idx
  ON chunks USING gin (metadata);

-- IVFFlat index for fast approximate nearest-neighbor vector search
-- lists=100 is suitable for up to ~1M vectors; tune higher for larger corpora
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- GIN index for PostgreSQL full-text search on chunk content
CREATE INDEX ON chunks USING gin (to_tsvector('english', content));

-- =============================================================================
-- 5. processing_runs: ingestion / analysis provenance
-- =============================================================================
CREATE TABLE processing_runs (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_type       TEXT NOT NULL,
  status         TEXT NOT NULL DEFAULT 'running',
  model          TEXT,
  prompt_version TEXT,
  code_version   TEXT,
  started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at    TIMESTAMPTZ,
  metadata       JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX processing_runs_run_type_idx
  ON processing_runs (run_type, started_at DESC);

-- =============================================================================
-- 6. entities: durable analyst primitives extracted from sources
-- =============================================================================
CREATE TABLE entities (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT NOT NULL,
  entity_type    TEXT NOT NULL,
  ticker         TEXT,
  metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (entity_type, canonical_name)
);

CREATE INDEX entities_canonical_name_idx
  ON entities (canonical_name);

CREATE INDEX entities_entity_type_idx
  ON entities (entity_type);

CREATE TABLE entity_aliases (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id   UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  alias       TEXT NOT NULL,
  alias_type  TEXT NOT NULL DEFAULT 'name',
  confidence  REAL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (entity_id, alias)
);

CREATE INDEX entity_aliases_alias_idx
  ON entity_aliases (alias);

CREATE TABLE entity_relationships (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_entity_id  UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  relation_type      TEXT NOT NULL,
  object_entity_id   UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  source_id          UUID REFERENCES sources(id) ON DELETE SET NULL,
  confidence         REAL,
  valid_from         TIMESTAMPTZ,
  valid_to           TIMESTAMPTZ,
  metadata           JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (subject_entity_id, relation_type, object_entity_id)
);

CREATE INDEX entity_relationships_subject_idx
  ON entity_relationships (subject_entity_id, relation_type);

CREATE INDEX entity_relationships_object_idx
  ON entity_relationships (object_entity_id, relation_type);

CREATE INDEX entity_relationships_source_idx
  ON entity_relationships (source_id);

CREATE TABLE source_entities (
  source_id      UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  entity_id      UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  role           TEXT NOT NULL DEFAULT 'mentioned',
  mention_count  INTEGER,
  salience       REAL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (source_id, entity_id, role)
);

CREATE INDEX source_entities_entity_idx
  ON source_entities (entity_id, source_id);

CREATE TABLE lenses (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  description TEXT
);

INSERT INTO lenses (slug, name, description) VALUES
  ('business-model', 'Business Model', 'Revenue model, margins, pricing, and monetization.'),
  ('distribution', 'Distribution', 'Default access, channel power, bundling, and go-to-market.'),
  ('platform', 'Platform Power', 'OS, ecosystem, control points, complements, and APIs.'),
  ('org-design', 'Org Design', 'Management structure, incentives, and operating model.'),
  ('supply-chain', 'Supply Chain', 'Capacity, manufacturing, hardware dependencies, and logistics.'),
  ('regulation', 'Regulation', 'Antitrust, policy, court rulings, and government action.'),
  ('security', 'Security', 'Security posture, trust boundaries, and risk containment.'),
  ('aggregation', 'Aggregation', 'Demand ownership, supplier leverage, and aggregation dynamics.'),
  ('bundling', 'Bundling', 'Package design, suite leverage, and cross-subsidy effects.'),
  ('capex', 'CapEx', 'Infrastructure spending, utilization, and fixed-cost leverage.')
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE claims (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id           UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  subject_entity_id   UUID REFERENCES entities(id) ON DELETE SET NULL,
  object_entity_id    UUID REFERENCES entities(id) ON DELETE SET NULL,
  claim_type          TEXT NOT NULL,
  modality            TEXT NOT NULL DEFAULT 'reported',
  stance              TEXT,
  claim_text          TEXT NOT NULL,
  normalized_claim    TEXT,
  event_at            TIMESTAMPTZ,
  event_end_at        TIMESTAMPTZ,
  confidence          REAL,
  importance          REAL,
  extraction_run_id   UUID REFERENCES processing_runs(id) ON DELETE SET NULL,
  metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX claims_source_id_idx
  ON claims (source_id);

CREATE INDEX claims_subject_entity_id_idx
  ON claims (subject_entity_id, event_at DESC);

CREATE INDEX claims_object_entity_id_idx
  ON claims (object_entity_id, event_at DESC);

CREATE INDEX claims_claim_type_idx
  ON claims (claim_type);

CREATE INDEX claims_event_at_idx
  ON claims (event_at DESC);

CREATE INDEX claims_modality_idx
  ON claims (modality);

CREATE INDEX claims_metadata_gin_idx
  ON claims USING gin (metadata);

CREATE TABLE claim_lenses (
  claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  lens_id     UUID NOT NULL REFERENCES lenses(id) ON DELETE CASCADE,
  weight      REAL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (claim_id, lens_id)
);

CREATE INDEX claim_lenses_lens_id_idx
  ON claim_lenses (lens_id, claim_id);

CREATE TABLE claim_evidence (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id      UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  source_id     UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  chunk_id      UUID REFERENCES chunks(id) ON DELETE SET NULL,
  evidence_text TEXT,
  start_char    INTEGER,
  end_char      INTEGER,
  confidence    REAL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX claim_evidence_claim_id_idx
  ON claim_evidence (claim_id);

CREATE INDEX claim_evidence_source_id_idx
  ON claim_evidence (source_id);

CREATE INDEX claim_evidence_chunk_id_idx
  ON claim_evidence (chunk_id);

CREATE TABLE claim_links (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_claim_id  UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  to_claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  link_type      TEXT NOT NULL,
  confidence     REAL,
  explanation    TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (from_claim_id, to_claim_id, link_type)
);

CREATE INDEX claim_links_from_idx
  ON claim_links (from_claim_id, link_type);

CREATE INDEX claim_links_to_idx
  ON claim_links (to_claim_id, link_type);

-- =============================================================================
-- 7. conversations: chat sessions between the user and the second brain
-- =============================================================================
CREATE TABLE conversations (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  title      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 8. messages: individual turns (user questions and assistant responses)
--    role must be 'user' or 'assistant' — enforced via CHECK constraint
-- =============================================================================
CREATE TABLE messages (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
  content         TEXT        NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 9. insights: digests plus Phase 4/5 analyst-facing suggestions and synthesis
--    'seen' tracks if user has viewed it. 'status' allows regeneration without
--    losing history. Linked entities / claims provide explainable provenance.
-- =============================================================================
CREATE TABLE insights (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  type              TEXT        NOT NULL,   -- 'digest', 'coverage_gap', 'counterpoint', 'follow_up', 'watch', ...
  title             TEXT        NOT NULL,
  body              TEXT        NOT NULL,
  seen              BOOLEAN     NOT NULL DEFAULT false,
  status            TEXT        NOT NULL DEFAULT 'active',
  summary           TEXT,
  metadata          JSONB       NOT NULL DEFAULT '{}'::jsonb,
  processing_run_id UUID        REFERENCES processing_runs(id) ON DELETE SET NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX insights_type_created_at_idx
  ON insights (type, created_at DESC);

CREATE INDEX insights_status_idx
  ON insights (status);

CREATE TABLE insight_claims (
  insight_id   UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
  claim_id     UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  role         TEXT NOT NULL DEFAULT 'support',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (insight_id, claim_id)
);

CREATE INDEX insight_claims_claim_id_idx
  ON insight_claims (claim_id);

CREATE TABLE insight_entities (
  insight_id   UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
  entity_id    UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  role         TEXT NOT NULL DEFAULT 'subject',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (insight_id, entity_id)
);

CREATE INDEX insight_entities_entity_id_idx
  ON insight_entities (entity_id);

-- =============================================================================
-- Hybrid search function: combines pgvector cosine similarity with PostgreSQL FTS
-- Apply to Supabase via: psql $DATABASE_URL -f schema.sql (idempotent: OR REPLACE)
--
-- Scoring weights (tunable here):
--   70% vector (semantic meaning) + 30% FTS (keyword relevance)
-- Vector-heavy because semantic similarity is the primary signal in a personal
-- knowledge base. Adjust the 0.7 / 0.3 constants below if you want more keyword
-- influence (e.g. 0.5 / 0.5 for equal weighting).
-- =============================================================================
DROP FUNCTION IF EXISTS hybrid_search(vector, text, integer, date, date);

CREATE OR REPLACE FUNCTION hybrid_search(
  query_embedding   vector(1536),
  query_text        text,
  match_count       int     DEFAULT 10,
  date_after        date    DEFAULT NULL,
  date_before       date    DEFAULT NULL
)
RETURNS TABLE (
  chunk_id      uuid,
  source_id     uuid,
  content       text,
  vector_score  float,
  fts_score     float,
  hybrid_score  float,
  title         text,
  author        text,
  url           text,
  published_at  timestamptz,
  kind          text,
  tier          text,
  publisher     text
)
LANGUAGE sql STABLE
AS $$
  -- Full-scan hybrid search: exact computation across all chunks.
  -- The corpus is small (~6K chunks), so a full scan is fast (<1s) and has
  -- perfect recall. The ivfflat index is intentionally bypassed here — its
  -- approximate search with probes=1 was missing relevant results.
  SELECT
    c.id                                                          AS chunk_id,
    c.source_id,
    c.content,
    1 - (c.embedding <=> query_embedding)                        AS vector_score,
    ts_rank(to_tsvector('english', c.content),
            plainto_tsquery('english', query_text))              AS fts_score,
    -- Hybrid: 70% vector similarity + 30% full-text rank
    -- Weights are tunable — edit the constants here and re-run this file
    0.7 * (1 - (c.embedding <=> query_embedding))
    + 0.3 * ts_rank(to_tsvector('english', c.content),
                    plainto_tsquery('english', query_text))      AS hybrid_score,
    s.title,
    s.author,
    s.url,
    s.published_at,
    s.kind,
    s.tier,
    s.publisher
  FROM chunks c
  JOIN sources s ON s.id = c.source_id
  WHERE
    c.embedding IS NOT NULL
    AND (date_after  IS NULL OR s.published_at >= date_after)
    AND (date_before IS NULL OR s.published_at <= date_before)
  ORDER BY hybrid_score DESC
  LIMIT match_count;
$$;

-- ============================================================
-- Phase 2 Additions: Cross-session memory on messages table
-- ============================================================

-- Add embedding column to messages for semantic search over past conversations
ALTER TABLE messages ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Add source-level embedding storage for Phase 3 topic preparation
ALTER TABLE sources ADD COLUMN IF NOT EXISTS source_embedding vector(1536);

-- Add topic centroid storage for Phase 3 incremental topic matching
ALTER TABLE topics ADD COLUMN IF NOT EXISTS centroid_embedding vector(1536);

-- IVFFlat index for semantic search over message embeddings
CREATE INDEX IF NOT EXISTS messages_embedding_idx
  ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- search_past_messages: semantic search over past assistant messages
-- Used by memory.py to inject relevant past conversation context
CREATE OR REPLACE FUNCTION search_past_messages(
  query_embedding vector(1536),
  exclude_conversation_id uuid,
  match_count int DEFAULT 3
)
RETURNS TABLE (
  message_id uuid,
  conv_id uuid,
  conv_title text,
  content text,
  created_at timestamptz,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    m.id          AS message_id,
    c.id          AS conv_id,
    c.title       AS conv_title,
    m.content,
    m.created_at,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM messages m
  JOIN conversations c ON c.id = m.conversation_id
  WHERE m.role = 'assistant'
    AND m.embedding IS NOT NULL
    AND m.conversation_id != exclude_conversation_id
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- match_topic: find the best matching topic centroid for a source embedding
CREATE OR REPLACE FUNCTION match_topic(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.65,
  match_count int DEFAULT 1
)
RETURNS TABLE (
  topic_id uuid,
  topic_name text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id AS topic_id,
    name AS topic_name,
    1 - (centroid_embedding <=> query_embedding) AS similarity
  FROM topics
  WHERE centroid_embedding IS NOT NULL
    AND 1 - (centroid_embedding <=> query_embedding) >= match_threshold
  ORDER BY centroid_embedding <=> query_embedding
  LIMIT match_count;
$$;

CREATE OR REPLACE VIEW entity_claim_timeline AS
SELECT
  c.id AS claim_id,
  c.subject_entity_id AS entity_id,
  subject_entity.canonical_name AS entity_name,
  'subject'::text AS entity_role,
  c.object_entity_id AS counterparty_entity_id,
  object_entity.canonical_name AS counterparty_entity_name,
  c.claim_type,
  c.modality,
  c.stance,
  c.claim_text,
  c.normalized_claim,
  c.event_at,
  c.importance,
  c.confidence,
  COALESCE(c.event_at, s.published_at, s.ingested_at, c.created_at) AS timeline_at,
  s.id AS source_id,
  s.title AS source_title,
  s.url AS source_url,
  s.source_type,
  s.kind AS source_kind,
  s.tier AS source_tier,
  s.published_at AS source_published_at,
  s.ingested_at AS source_ingested_at
FROM claims c
JOIN sources s ON s.id = c.source_id
LEFT JOIN entities subject_entity ON subject_entity.id = c.subject_entity_id
LEFT JOIN entities object_entity ON object_entity.id = c.object_entity_id
WHERE c.subject_entity_id IS NOT NULL

UNION ALL

SELECT
  c.id AS claim_id,
  c.object_entity_id AS entity_id,
  object_entity.canonical_name AS entity_name,
  'object'::text AS entity_role,
  c.subject_entity_id AS counterparty_entity_id,
  subject_entity.canonical_name AS counterparty_entity_name,
  c.claim_type,
  c.modality,
  c.stance,
  c.claim_text,
  c.normalized_claim,
  c.event_at,
  c.importance,
  c.confidence,
  COALESCE(c.event_at, s.published_at, s.ingested_at, c.created_at) AS timeline_at,
  s.id AS source_id,
  s.title AS source_title,
  s.url AS source_url,
  s.source_type,
  s.kind AS source_kind,
  s.tier AS source_tier,
  s.published_at AS source_published_at,
  s.ingested_at AS source_ingested_at
FROM claims c
JOIN sources s ON s.id = c.source_id
LEFT JOIN entities subject_entity ON subject_entity.id = c.subject_entity_id
LEFT JOIN entities object_entity ON object_entity.id = c.object_entity_id
WHERE c.object_entity_id IS NOT NULL;

-- =============================================================================
-- Second Brain — Full Database Schema
-- Apply once to Supabase: psql $DATABASE_URL -f schema.sql
-- =============================================================================

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 1. sources: one row per Readwise article
--    readwise_id ensures we never ingest the same article twice
-- =============================================================================
CREATE TABLE sources (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  readwise_id  TEXT        UNIQUE NOT NULL,          -- Readwise article ID for deduplication
  title        TEXT        NOT NULL,
  author       TEXT,
  url          TEXT,
  source_type  TEXT        NOT NULL DEFAULT 'readwise_reader',
  published_at TIMESTAMPTZ,
  ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_text     TEXT                                  -- full article text for full-text search
);

-- =============================================================================
-- 2. topics: auto-assigned clusters (populated in Phase 3 — Clustering)
--    These are not user-defined tags; they are computed from embeddings.
-- =============================================================================
CREATE TABLE topics (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT        NOT NULL,
  summary    TEXT,
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
  content     TEXT    NOT NULL,
  token_count INTEGER,
  embedding   vector(1536),              -- text-embedding-3-small = 1536 dimensions
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- IVFFlat index for fast approximate nearest-neighbor vector search
-- lists=100 is suitable for up to ~1M vectors; tune higher for larger corpora
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- GIN index for PostgreSQL full-text search on chunk content
CREATE INDEX ON chunks USING gin (to_tsvector('english', content));

-- =============================================================================
-- 5. conversations: chat sessions between the user and the second brain
-- =============================================================================
CREATE TABLE conversations (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  title      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 6. messages: individual turns (user questions and assistant responses)
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
-- 7. insights: proactively detected patterns, contradictions, weekly digests
--    Populated in Phase 5 — Proactive Insights. 'seen' tracks if user has viewed it.
-- =============================================================================
CREATE TABLE insights (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  type       TEXT        NOT NULL,              -- 'pattern', 'contradiction', 'digest'
  title      TEXT        NOT NULL,
  body       TEXT        NOT NULL,
  seen       BOOLEAN     NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
  published_at  timestamptz
)
LANGUAGE sql STABLE
AS $$
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
    s.published_at
  FROM chunks c
  JOIN sources s ON s.id = c.source_id
  WHERE
    c.embedding IS NOT NULL
    AND (date_after  IS NULL OR s.published_at >= date_after)
    AND (date_before IS NULL OR s.published_at <= date_before)
  ORDER BY hybrid_score DESC
  LIMIT match_count;
$$;

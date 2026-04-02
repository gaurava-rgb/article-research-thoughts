-- =============================================================================
-- Phase 1: Analyst Workbench Foundation Patch
-- Apply on top of the current v1 schema to preserve existing data.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE sources
  ALTER COLUMN readwise_id DROP NOT NULL;

ALTER TABLE sources
  ADD COLUMN IF NOT EXISTS external_id TEXT,
  ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'article',
  ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'analysis',
  ADD COLUMN IF NOT EXISTS publisher TEXT,
  ADD COLUMN IF NOT EXISTS remote_updated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS parent_source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS thread_key TEXT,
  ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'en',
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS checksum TEXT;

UPDATE sources
SET
  source_type = COALESCE(NULLIF(source_type, ''), 'readwise'),
  external_id = COALESCE(external_id, readwise_id),
  kind = COALESCE(kind, 'article'),
  tier = COALESCE(tier, 'analysis'),
  language = COALESCE(language, 'en')
WHERE external_id IS NULL
   OR source_type = 'readwise_reader';

CREATE UNIQUE INDEX IF NOT EXISTS sources_source_type_external_id_idx
  ON sources (source_type, external_id)
  WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS sources_kind_idx
  ON sources (kind);

CREATE INDEX IF NOT EXISTS sources_tier_idx
  ON sources (tier);

CREATE INDEX IF NOT EXISTS sources_published_at_idx
  ON sources (published_at DESC);

CREATE INDEX IF NOT EXISTS sources_parent_source_id_idx
  ON sources (parent_source_id);

CREATE INDEX IF NOT EXISTS sources_thread_key_idx
  ON sources (thread_key);

CREATE INDEX IF NOT EXISTS sources_publisher_idx
  ON sources (publisher);

CREATE INDEX IF NOT EXISTS sources_metadata_gin_idx
  ON sources USING gin (metadata);

ALTER TABLE chunks
  ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'chunk',
  ADD COLUMN IF NOT EXISTS section_label TEXT,
  ADD COLUMN IF NOT EXISTS speaker TEXT,
  ADD COLUMN IF NOT EXISTS page_number INTEGER,
  ADD COLUMN IF NOT EXISTS start_char INTEGER,
  ADD COLUMN IF NOT EXISTS end_char INTEGER,
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS chunks_source_id_chunk_index_idx
  ON chunks (source_id, chunk_index);

CREATE INDEX IF NOT EXISTS chunks_kind_idx
  ON chunks (kind);

CREATE INDEX IF NOT EXISTS chunks_speaker_idx
  ON chunks (speaker);

CREATE INDEX IF NOT EXISTS chunks_section_label_idx
  ON chunks (section_label);

CREATE INDEX IF NOT EXISTS chunks_metadata_gin_idx
  ON chunks USING gin (metadata);

CREATE TABLE IF NOT EXISTS processing_runs (
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

CREATE INDEX IF NOT EXISTS processing_runs_run_type_idx
  ON processing_runs (run_type, started_at DESC);

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
  SELECT
    c.id                                                          AS chunk_id,
    c.source_id,
    c.content,
    1 - (c.embedding <=> query_embedding)                        AS vector_score,
    ts_rank(to_tsvector('english', c.content),
            plainto_tsquery('english', query_text))              AS fts_score,
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

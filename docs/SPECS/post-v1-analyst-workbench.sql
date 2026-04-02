-- =============================================================================
-- Post-v1 Analyst Workbench Schema
-- Additive migration on top of the current v1 schema.
--
-- Goal:
--   Keep the current `sources` / `chunks` / chat stack intact while adding
--   the structured-analysis layer needed for mixed-source, timeline-aware,
--   ripple-aware synthesis.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 1. Generalize sources without renaming the table
-- =============================================================================

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

COMMENT ON COLUMN sources.source_type IS
  'Connector/system for this artifact, e.g. readwise, twitter, podcast, sec, upload.';

COMMENT ON COLUMN sources.kind IS
  'Artifact kind, e.g. article, transcript, thread, earnings_call, filing, note, deck.';

COMMENT ON COLUMN sources.tier IS
  'Analytical tier, e.g. primary, reporting, analysis, social, personal.';

COMMENT ON COLUMN sources.readwise_id IS
  'Legacy Readwise-only identifier. Deprecated in favor of external_id.';

-- =============================================================================
-- 2. Generalize chunks into structured retrieval/evidence segments
-- =============================================================================

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

-- =============================================================================
-- 3. Processing provenance
-- =============================================================================

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

-- =============================================================================
-- 4. Entity layer
-- =============================================================================

CREATE TABLE IF NOT EXISTS entities (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT NOT NULL,
  entity_type    TEXT NOT NULL,
  ticker         TEXT,
  metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (entity_type, canonical_name)
);

CREATE INDEX IF NOT EXISTS entities_canonical_name_idx
  ON entities (canonical_name);

CREATE INDEX IF NOT EXISTS entities_entity_type_idx
  ON entities (entity_type);

CREATE TABLE IF NOT EXISTS entity_aliases (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id   UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  alias       TEXT NOT NULL,
  alias_type  TEXT NOT NULL DEFAULT 'name',
  confidence  REAL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (entity_id, alias)
);

CREATE INDEX IF NOT EXISTS entity_aliases_alias_idx
  ON entity_aliases (alias);

CREATE TABLE IF NOT EXISTS entity_relationships (
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

CREATE INDEX IF NOT EXISTS entity_relationships_subject_idx
  ON entity_relationships (subject_entity_id, relation_type);

CREATE INDEX IF NOT EXISTS entity_relationships_object_idx
  ON entity_relationships (object_entity_id, relation_type);

CREATE INDEX IF NOT EXISTS entity_relationships_source_idx
  ON entity_relationships (source_id);

CREATE TABLE IF NOT EXISTS source_entities (
  source_id      UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  entity_id      UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  role           TEXT NOT NULL DEFAULT 'mentioned',
  mention_count  INTEGER,
  salience       REAL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (source_id, entity_id, role)
);

CREATE INDEX IF NOT EXISTS source_entities_entity_idx
  ON source_entities (entity_id, source_id);

-- =============================================================================
-- 5. Lens layer
-- =============================================================================

CREATE TABLE IF NOT EXISTS lenses (
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

-- =============================================================================
-- 6. Claims and evidence
-- =============================================================================

CREATE TABLE IF NOT EXISTS claims (
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

CREATE INDEX IF NOT EXISTS claims_source_id_idx
  ON claims (source_id);

CREATE INDEX IF NOT EXISTS claims_subject_entity_id_idx
  ON claims (subject_entity_id, event_at DESC);

CREATE INDEX IF NOT EXISTS claims_object_entity_id_idx
  ON claims (object_entity_id, event_at DESC);

CREATE INDEX IF NOT EXISTS claims_claim_type_idx
  ON claims (claim_type);

CREATE INDEX IF NOT EXISTS claims_event_at_idx
  ON claims (event_at DESC);

CREATE INDEX IF NOT EXISTS claims_modality_idx
  ON claims (modality);

CREATE INDEX IF NOT EXISTS claims_metadata_gin_idx
  ON claims USING gin (metadata);

CREATE TABLE IF NOT EXISTS claim_lenses (
  claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  lens_id     UUID NOT NULL REFERENCES lenses(id) ON DELETE CASCADE,
  weight      REAL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (claim_id, lens_id)
);

CREATE INDEX IF NOT EXISTS claim_lenses_lens_id_idx
  ON claim_lenses (lens_id, claim_id);

CREATE TABLE IF NOT EXISTS claim_evidence (
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

CREATE INDEX IF NOT EXISTS claim_evidence_claim_id_idx
  ON claim_evidence (claim_id);

CREATE INDEX IF NOT EXISTS claim_evidence_source_id_idx
  ON claim_evidence (source_id);

CREATE INDEX IF NOT EXISTS claim_evidence_chunk_id_idx
  ON claim_evidence (chunk_id);

CREATE TABLE IF NOT EXISTS claim_links (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_claim_id  UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  to_claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  link_type      TEXT NOT NULL,
  confidence     REAL,
  explanation    TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (from_claim_id, to_claim_id, link_type)
);

CREATE INDEX IF NOT EXISTS claim_links_from_idx
  ON claim_links (from_claim_id, link_type);

CREATE INDEX IF NOT EXISTS claim_links_to_idx
  ON claim_links (to_claim_id, link_type);

-- =============================================================================
-- 7. Upgrade insights from prose blobs to evidence-backed records
-- =============================================================================

ALTER TABLE insights
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS summary TEXT,
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS processing_run_id UUID REFERENCES processing_runs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS insights_type_created_at_idx
  ON insights (type, created_at DESC);

CREATE INDEX IF NOT EXISTS insights_status_idx
  ON insights (status);

CREATE TABLE IF NOT EXISTS insight_claims (
  insight_id   UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
  claim_id     UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  role         TEXT NOT NULL DEFAULT 'support',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (insight_id, claim_id)
);

CREATE INDEX IF NOT EXISTS insight_claims_claim_id_idx
  ON insight_claims (claim_id);

CREATE TABLE IF NOT EXISTS insight_entities (
  insight_id   UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
  entity_id    UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  role         TEXT NOT NULL DEFAULT 'subject',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (insight_id, entity_id)
);

CREATE INDEX IF NOT EXISTS insight_entities_entity_id_idx
  ON insight_entities (entity_id);

-- =============================================================================
-- 8. Helpful view: entity timeline
-- =============================================================================

CREATE OR REPLACE VIEW entity_claim_timeline AS
SELECT
  c.id                  AS claim_id,
  e.id                  AS entity_id,
  e.canonical_name      AS entity_name,
  c.claim_type,
  c.modality,
  c.stance,
  c.claim_text,
  c.normalized_claim,
  COALESCE(c.event_at, s.published_at, s.ingested_at) AS timeline_at,
  s.id                  AS source_id,
  s.title               AS source_title,
  s.url                 AS source_url,
  s.source_type,
  s.kind                AS source_kind,
  s.tier                AS source_tier
FROM claims c
LEFT JOIN entities e ON e.id = c.subject_entity_id
JOIN sources s ON s.id = c.source_id;

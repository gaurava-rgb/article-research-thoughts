-- =============================================================================
-- Phase 2: Claims And Evidence
-- Apply on top of Phase 1 to add extractable analytical primitives.
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

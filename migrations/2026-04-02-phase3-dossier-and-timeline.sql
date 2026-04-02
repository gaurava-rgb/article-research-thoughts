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

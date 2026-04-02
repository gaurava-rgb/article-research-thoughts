export interface Source {
  sourceId?: string;
  title: string;
  url: string | null;
  author: string | null;
  score: number;
  publishedAt?: string | null;
  kind?: string | null;
  tier?: string | null;
  publisher?: string | null;
}

export interface SourceDetail {
  id: string;
  title: string;
  author: string | null;
  url: string | null;
  publishedAt: string | null;
  ingestedAt: string;
  updatedAt: string;
  sourceType: string;
  readwiseId: string | null;
  externalId: string | null;
  kind: string;
  tier: string;
  publisher: string | null;
  remoteUpdatedAt: string | null;
  parentSourceId: string | null;
  threadKey: string | null;
  language: string;
  metadata: Record<string, unknown>;
  analysis?: SourceAnalysis;
  latestAnalysisRun?: AnalysisRun | null;
}

export interface AnalysisRun {
  id: string;
  status: string;
  model: string | null;
  promptVersion: string | null;
  startedAt: string;
  finishedAt: string | null;
  metadata: Record<string, unknown>;
}

export interface SourceEntityAlias {
  entity_id: string;
  alias: string;
  alias_type: string;
  confidence: number | null;
}

export interface SourceEntity {
  id: string;
  canonical_name: string;
  entity_type: string;
  ticker: string | null;
  metadata: Record<string, unknown>;
  role: string | null;
  mention_count: number | null;
  salience: number | null;
  aliases: SourceEntityAlias[];
}

export interface ClaimLens {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  weight: number | null;
}

export interface ClaimEvidence {
  id: string;
  claim_id: string;
  source_id: string;
  chunk_id: string | null;
  evidence_text: string | null;
  start_char: number | null;
  end_char: number | null;
  confidence: number | null;
  created_at: string;
  chunk_index: number | null;
}

export interface ClaimLink {
  id: string;
  from_claim_id: string;
  to_claim_id: string;
  link_type: string;
  confidence: number | null;
  explanation: string | null;
  created_at: string;
  target_claim_text: string | null;
}

export interface SourceClaim {
  id: string;
  source_id: string;
  subject_entity_id: string | null;
  object_entity_id: string | null;
  claim_type: string;
  modality: string;
  stance: string | null;
  claim_text: string;
  normalized_claim: string | null;
  event_at: string | null;
  event_end_at: string | null;
  confidence: number | null;
  importance: number | null;
  extraction_run_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  subject_entity: SourceEntity | null;
  object_entity: SourceEntity | null;
  evidence: ClaimEvidence[];
  lenses: ClaimLens[];
  links: ClaimLink[];
}

export interface SourceAnalysis {
  entities: SourceEntity[];
  claims: SourceClaim[];
}

export interface EntityDirectoryItem {
  id: string;
  canonicalName: string;
  entityType: string;
  ticker: string | null;
  metadata: Record<string, unknown>;
  aliases: string[];
  aliasCount: number;
  sourceCount: number;
  claimCount: number;
  latestTimelineAt: string | null;
  latestClaimText: string | null;
}

export interface EntityRelationItem {
  id: string;
  direction: "incoming" | "outgoing";
  relationType: string;
  confidence: number | null;
  validFrom: string | null;
  validTo: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  counterpartyEntity: SourceEntity | null;
  source: {
    id: string | null;
    title: string | null;
    url: string | null;
    sourceType: string | null;
    kind: string | null;
    tier: string | null;
    publishedAt: string | null;
    ingestedAt: string | null;
  } | null;
}

export interface EntityRelationGroup {
  relationType: string;
  label: string;
  items: EntityRelationItem[];
}

export interface EntityTimelineLink {
  id: string;
  direction: "incoming" | "outgoing";
  linkType: string;
  confidence: number | null;
  explanation: string | null;
  createdAt: string;
  relatedClaimId: string;
  relatedClaimText: string | null;
}

export type EntityTimelineClaim = Omit<SourceClaim, "links"> & {
  timelineAt: string | null;
  entityRole: "subject" | "object" | null;
  counterpartyEntity: SourceEntity | null;
  source: {
    id: string | null;
    title: string | null;
    url: string | null;
    sourceType: string | null;
    kind: string | null;
    tier: string | null;
    publishedAt: string | null;
    ingestedAt: string | null;
  };
  links: EntityTimelineLink[];
  isContradictory: boolean;
  contradictionCount: number;
}

export interface EntityCurrentThesis {
  summary: string;
  sourceCount: number;
  claimCount: number;
  topClaims: EntityTimelineClaim[];
  dominantLenses: Array<{ name: string; count: number }>;
  claimTypeBreakdown: Array<{ claimType: string; count: number }>;
}

export interface EntityRecentChanges {
  summary: string;
  windowDays: number;
  items: EntityTimelineClaim[];
}

export interface EntityDossier {
  entity: SourceEntity;
  currentThesis: EntityCurrentThesis;
  recentChanges: EntityRecentChanges;
  relationships: EntityRelationGroup[];
  timeline: EntityTimelineClaim[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[]; // Only present on assistant messages returned from /api/chat
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Insight {
  id: string;
  type: "pattern" | "contradiction" | "digest";
  title: string;
  body: string;
  seen: boolean;
  createdAt: string;
}

export interface RelatedConversation {
  conversation_id: string;
  title: string;
  date: string;
  similarity: number;
}

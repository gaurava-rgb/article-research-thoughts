import type {
  AnalysisRun,
  Conversation,
  EntityDirectoryItem,
  EntityDossier,
  EntityRelationGroup,
  EntityTimelineClaim,
  Insight,
  Message,
  RelatedConversation,
  Source,
  SourceAnalysis,
  SourceClaim,
  SourceDetail,
  SourceEntity,
} from "./types";

// Base URL: empty string in production (same-origin via vercel.json rewrites),
// http://localhost:8000 in development (set via NEXT_PUBLIC_API_URL env var or defaults to "").
// next.config.ts rewrites handle the dev proxying so we use "" here always.
const BASE = "";

export async function createConversation(): Promise<Conversation> {
  const res = await fetch(`${BASE}/api/conversations`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`);
  const data = await res.json();
  return {
    id: data.id,
    title: data.title ?? null,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/api/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.status}`);
  const data: unknown[] = await res.json();
  return (data as Array<Record<string, string>>).map((c) => ({
    id: c.id,
    title: c.title ?? null,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
  }));
}

export async function fetchMessages(conversationId: string): Promise<Message[]> {
  const res = await fetch(`${BASE}/api/conversations/${conversationId}/messages`);
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
  const data: unknown[] = await res.json();
  return (data as Array<Record<string, string>>).map((m) => ({
    id: m.id,
    role: m.role as "user" | "assistant",
    content: m.content,
    createdAt: m.created_at,
  }));
}

export async function fetchInsights(): Promise<{ insights: Insight[]; unseen_count: number }> {
  const res = await fetch(`${BASE}/api/insights`);
  if (!res.ok) throw new Error(`Failed to fetch insights: ${res.status}`);
  const data = await res.json() as { insights: Array<Record<string, unknown>>; unseen_count: number };
  return {
    insights: data.insights.map((i) => ({
      id: i.id as string,
      type: i.type as Insight["type"],
      title: i.title as string,
      body: i.body as string,
      summary: (i.summary as string | null | undefined) ?? null,
      status: (i.status as string | undefined) ?? "active",
      metadata: (i.metadata as Record<string, unknown> | undefined) ?? {},
      entities: ((i.entities as Array<Record<string, unknown>> | undefined) ?? []).map((entity) => ({
        id: entity.id as string,
        canonicalName: entity.canonical_name as string,
        entityType: entity.entity_type as string,
        ticker: (entity.ticker as string | null | undefined) ?? null,
        role: (entity.role as string | null | undefined) ?? null,
        metadata: (entity.metadata as Record<string, unknown> | undefined) ?? {},
      })),
      claims: ((i.claims as Array<Record<string, unknown>> | undefined) ?? []).map((claim) => ({
        id: claim.id as string,
        claimText: claim.claim_text as string,
        claimType: claim.claim_type as string,
        importance: (claim.importance as number | null | undefined) ?? null,
        confidence: (claim.confidence as number | null | undefined) ?? null,
        role: (claim.role as string | null | undefined) ?? null,
        subjectEntityName: (claim.subject_entity_name as string | null | undefined) ?? null,
      })),
      seen: i.seen as boolean,
      createdAt: i.created_at as string,
    })),
    unseen_count: data.unseen_count,
  };
}

export async function markInsightSeen(insightId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/insights/${insightId}/seen`, { method: "PATCH" });
  if (!res.ok) throw new Error(`Failed to mark insight seen: ${res.status}`);
}

export async function generateDigest(): Promise<{ status: string; message?: string; insight?: Insight }> {
  const res = await fetch(`${BASE}/api/insights/generate-digest`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to generate digest: ${res.status}`);
  return res.json() as Promise<{ status: string; message?: string; insight?: Insight }>;
}

export async function generateSuggestions(): Promise<{ status: string; message?: string; insights: Insight[] }> {
  const res = await fetch(`${BASE}/api/insights/generate-suggestions`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to generate suggestions: ${res.status}`);
  const data = await res.json() as { status: string; message?: string; insights?: Array<Record<string, unknown>> };
  return {
    status: data.status,
    message: data.message,
    insights: ((data.insights as Array<Record<string, unknown>> | undefined) ?? []).map((i) => ({
      id: i.id as string,
      type: i.type as Insight["type"],
      title: i.title as string,
      body: i.body as string,
      summary: (i.summary as string | null | undefined) ?? null,
      status: (i.status as string | undefined) ?? "active",
      metadata: (i.metadata as Record<string, unknown> | undefined) ?? {},
      entities: ((i.entities as Array<Record<string, unknown>> | undefined) ?? []).map((entity) => ({
        id: entity.id as string,
        canonicalName: entity.canonical_name as string,
        entityType: entity.entity_type as string,
        ticker: (entity.ticker as string | null | undefined) ?? null,
        role: (entity.role as string | null | undefined) ?? null,
        metadata: (entity.metadata as Record<string, unknown> | undefined) ?? {},
      })),
      claims: ((i.claims as Array<Record<string, unknown>> | undefined) ?? []).map((claim) => ({
        id: claim.id as string,
        claimText: claim.claim_text as string,
        claimType: claim.claim_type as string,
        importance: (claim.importance as number | null | undefined) ?? null,
        confidence: (claim.confidence as number | null | undefined) ?? null,
        role: (claim.role as string | null | undefined) ?? null,
        subjectEntityName: (claim.subject_entity_name as string | null | undefined) ?? null,
      })),
      seen: i.seen as boolean,
      createdAt: i.created_at as string,
    })),
  };
}

export async function fetchSimilarConversations(
  query: string,
  excludeId: string,
): Promise<RelatedConversation[]> {
  const params = new URLSearchParams({ query, exclude_id: excludeId });
  const res = await fetch(`${BASE}/api/conversations/similar?${params}`);
  if (!res.ok) return [];
  return res.json() as Promise<RelatedConversation[]>;
}

export async function fetchSourceDetail(sourceId: string): Promise<SourceDetail> {
  const res = await fetch(`${BASE}/api/sources/${sourceId}`);
  if (!res.ok) throw new Error(`Failed to fetch source detail: ${res.status}`);
  const data = await res.json() as Record<string, unknown>;
  const analysisData = (data.analysis as Record<string, unknown> | undefined) ?? undefined;
  const latestRun = (data.latest_analysis_run as Record<string, unknown> | null | undefined) ?? null;
  return {
    id: data.id as string,
    title: data.title as string,
    author: (data.author as string | null) ?? null,
    url: (data.url as string | null) ?? null,
    publishedAt: (data.published_at as string | null) ?? null,
    ingestedAt: data.ingested_at as string,
    updatedAt: data.updated_at as string,
    sourceType: data.source_type as string,
    readwiseId: (data.readwise_id as string | null) ?? null,
    externalId: (data.external_id as string | null) ?? null,
    kind: data.kind as string,
    tier: data.tier as string,
    publisher: (data.publisher as string | null) ?? null,
    remoteUpdatedAt: (data.remote_updated_at as string | null) ?? null,
    parentSourceId: (data.parent_source_id as string | null) ?? null,
    threadKey: (data.thread_key as string | null) ?? null,
    language: data.language as string,
    metadata: (data.metadata as Record<string, unknown>) ?? {},
    analysis: analysisData ? mapSourceAnalysis(analysisData) : undefined,
    latestAnalysisRun: latestRun ? mapAnalysisRun(latestRun) : null,
  };
}

export async function fetchEntityDirectory(): Promise<EntityDirectoryItem[]> {
  const res = await fetch(`${BASE}/api/entities`);
  if (!res.ok) throw new Error(`Failed to fetch entity directory: ${res.status}`);
  const data = await res.json() as Array<Record<string, unknown>>;
  return data.map((entity) => ({
    id: entity.id as string,
    canonicalName: entity.canonical_name as string,
    entityType: entity.entity_type as string,
    ticker: (entity.ticker as string | null) ?? null,
    metadata: (entity.metadata as Record<string, unknown>) ?? {},
    aliases: ((entity.aliases as string[] | undefined) ?? []).map((alias) => String(alias)),
    aliasCount: (entity.alias_count as number | null) ?? 0,
    sourceCount: (entity.source_count as number | null) ?? 0,
    claimCount: (entity.claim_count as number | null) ?? 0,
    latestTimelineAt: (entity.latest_timeline_at as string | null) ?? null,
    latestClaimText: (entity.latest_claim_text as string | null) ?? null,
  }));
}

export async function fetchEntityDossier(entityId: string): Promise<EntityDossier> {
  const res = await fetch(`${BASE}/api/entities/${entityId}`);
  if (!res.ok) throw new Error(`Failed to fetch entity dossier: ${res.status}`);
  const data = await res.json() as Record<string, unknown>;
  return {
    entity: mapSourceEntity(data.entity as Record<string, unknown>),
    currentThesis: mapEntityCurrentThesis(data.current_thesis as Record<string, unknown>),
    recentChanges: mapEntityRecentChanges(data.recent_changes as Record<string, unknown>),
    relationships: ((data.relationships as Array<Record<string, unknown>> | undefined) ?? []).map(
      mapEntityRelationGroup,
    ),
    timeline: ((data.timeline as Array<Record<string, unknown>> | undefined) ?? []).map(mapEntityTimelineClaim),
  };
}

function mapAnalysisRun(run: Record<string, unknown>): AnalysisRun {
  return {
    id: run.id as string,
    status: run.status as string,
    model: (run.model as string | null) ?? null,
    promptVersion: (run.prompt_version as string | null) ?? null,
    startedAt: run.started_at as string,
    finishedAt: (run.finished_at as string | null) ?? null,
    metadata: (run.metadata as Record<string, unknown>) ?? {},
  };
}

function mapSourceEntity(entity: Record<string, unknown>): SourceEntity {
  return {
    id: entity.id as string,
    canonical_name: entity.canonical_name as string,
    entity_type: entity.entity_type as string,
    ticker: (entity.ticker as string | null) ?? null,
    metadata: (entity.metadata as Record<string, unknown>) ?? {},
    role: (entity.role as string | null) ?? null,
    mention_count: (entity.mention_count as number | null) ?? null,
    salience: (entity.salience as number | null) ?? null,
    aliases: ((entity.aliases as Array<Record<string, unknown>> | undefined) ?? []).map((alias) => ({
      entity_id: alias.entity_id as string,
      alias: alias.alias as string,
      alias_type: alias.alias_type as string,
      confidence: (alias.confidence as number | null) ?? null,
    })),
  };
}

function mapSourceClaim(claim: Record<string, unknown>): SourceClaim {
  return {
    id: claim.id as string,
    source_id: claim.source_id as string,
    subject_entity_id: (claim.subject_entity_id as string | null) ?? null,
    object_entity_id: (claim.object_entity_id as string | null) ?? null,
    claim_type: claim.claim_type as string,
    modality: claim.modality as string,
    stance: (claim.stance as string | null) ?? null,
    claim_text: claim.claim_text as string,
    normalized_claim: (claim.normalized_claim as string | null) ?? null,
    event_at: (claim.event_at as string | null) ?? null,
    event_end_at: (claim.event_end_at as string | null) ?? null,
    confidence: (claim.confidence as number | null) ?? null,
    importance: (claim.importance as number | null) ?? null,
    extraction_run_id: (claim.extraction_run_id as string | null) ?? null,
    metadata: (claim.metadata as Record<string, unknown>) ?? {},
    created_at: claim.created_at as string,
    subject_entity: claim.subject_entity ? mapSourceEntity(claim.subject_entity as Record<string, unknown>) : null,
    object_entity: claim.object_entity ? mapSourceEntity(claim.object_entity as Record<string, unknown>) : null,
    evidence: ((claim.evidence as Array<Record<string, unknown>> | undefined) ?? []).map((evidence) => ({
      id: evidence.id as string,
      claim_id: evidence.claim_id as string,
      source_id: evidence.source_id as string,
      chunk_id: (evidence.chunk_id as string | null) ?? null,
      evidence_text: (evidence.evidence_text as string | null) ?? null,
      start_char: (evidence.start_char as number | null) ?? null,
      end_char: (evidence.end_char as number | null) ?? null,
      confidence: (evidence.confidence as number | null) ?? null,
      created_at: evidence.created_at as string,
      chunk_index: (evidence.chunk_index as number | null) ?? null,
    })),
    lenses: ((claim.lenses as Array<Record<string, unknown>> | undefined) ?? []).map((lens) => ({
      id: lens.id as string,
      slug: lens.slug as string,
      name: lens.name as string,
      description: (lens.description as string | null) ?? null,
      weight: (lens.weight as number | null) ?? null,
    })),
    links: ((claim.links as Array<Record<string, unknown>> | undefined) ?? []).map((link) => ({
      id: link.id as string,
      from_claim_id: link.from_claim_id as string,
      to_claim_id: link.to_claim_id as string,
      link_type: link.link_type as string,
      confidence: (link.confidence as number | null) ?? null,
      explanation: (link.explanation as string | null) ?? null,
      created_at: link.created_at as string,
      target_claim_text: (link.target_claim_text as string | null) ?? null,
    })),
  };
}

function mapEntityTimelineClaim(claim: Record<string, unknown>): EntityTimelineClaim {
  const mappedClaim = mapSourceClaim(claim);
  return {
    ...mappedClaim,
    timelineAt: (claim.timeline_at as string | null) ?? null,
    entityRole: (claim.entity_role as "subject" | "object" | null) ?? null,
    counterpartyEntity: claim.counterparty_entity
      ? mapSourceEntity(claim.counterparty_entity as Record<string, unknown>)
      : null,
    source: {
      id: ((claim.source as Record<string, unknown> | undefined)?.id as string | null) ?? null,
      title: ((claim.source as Record<string, unknown> | undefined)?.title as string | null) ?? null,
      url: ((claim.source as Record<string, unknown> | undefined)?.url as string | null) ?? null,
      sourceType: ((claim.source as Record<string, unknown> | undefined)?.source_type as string | null) ?? null,
      kind: ((claim.source as Record<string, unknown> | undefined)?.kind as string | null) ?? null,
      tier: ((claim.source as Record<string, unknown> | undefined)?.tier as string | null) ?? null,
      publishedAt: ((claim.source as Record<string, unknown> | undefined)?.published_at as string | null) ?? null,
      ingestedAt: ((claim.source as Record<string, unknown> | undefined)?.ingested_at as string | null) ?? null,
    },
    links: ((claim.links as Array<Record<string, unknown>> | undefined) ?? []).map((link) => ({
      id: link.id as string,
      direction: link.direction as "incoming" | "outgoing",
      linkType: link.link_type as string,
      confidence: (link.confidence as number | null) ?? null,
      explanation: (link.explanation as string | null) ?? null,
      createdAt: link.created_at as string,
      relatedClaimId: link.related_claim_id as string,
      relatedClaimText: (link.related_claim_text as string | null) ?? null,
    })),
    isContradictory: Boolean(claim.is_contradictory),
    contradictionCount: (claim.contradiction_count as number | null) ?? 0,
  };
}

function mapEntityRelationGroup(group: Record<string, unknown>): EntityRelationGroup {
  return {
    relationType: group.relation_type as string,
    label: group.label as string,
    items: ((group.items as Array<Record<string, unknown>> | undefined) ?? []).map((item) => ({
      id: item.id as string,
      direction: item.direction as "incoming" | "outgoing",
      relationType: item.relation_type as string,
      confidence: (item.confidence as number | null) ?? null,
      validFrom: (item.valid_from as string | null) ?? null,
      validTo: (item.valid_to as string | null) ?? null,
      metadata: (item.metadata as Record<string, unknown>) ?? {},
      createdAt: item.created_at as string,
      counterpartyEntity: item.counterparty_entity
        ? mapSourceEntity(item.counterparty_entity as Record<string, unknown>)
        : null,
      source: item.source
        ? {
            id: ((item.source as Record<string, unknown>).id as string | null) ?? null,
            title: ((item.source as Record<string, unknown>).title as string | null) ?? null,
            url: ((item.source as Record<string, unknown>).url as string | null) ?? null,
            sourceType: ((item.source as Record<string, unknown>).source_type as string | null) ?? null,
            kind: ((item.source as Record<string, unknown>).kind as string | null) ?? null,
            tier: ((item.source as Record<string, unknown>).tier as string | null) ?? null,
            publishedAt: ((item.source as Record<string, unknown>).published_at as string | null) ?? null,
            ingestedAt: ((item.source as Record<string, unknown>).ingested_at as string | null) ?? null,
          }
        : null,
    })),
  };
}

function mapEntityCurrentThesis(thesis: Record<string, unknown>) {
  return {
    summary: thesis.summary as string,
    sourceCount: (thesis.source_count as number | null) ?? 0,
    claimCount: (thesis.claim_count as number | null) ?? 0,
    topClaims: ((thesis.top_claims as Array<Record<string, unknown>> | undefined) ?? []).map(mapEntityTimelineClaim),
    dominantLenses: ((thesis.dominant_lenses as Array<Record<string, unknown>> | undefined) ?? []).map((lens) => ({
      name: lens.name as string,
      count: lens.count as number,
    })),
    claimTypeBreakdown: ((thesis.claim_type_breakdown as Array<Record<string, unknown>> | undefined) ?? []).map((item) => ({
      claimType: item.claim_type as string,
      count: item.count as number,
    })),
  };
}

function mapEntityRecentChanges(recentChanges: Record<string, unknown>) {
  return {
    summary: recentChanges.summary as string,
    windowDays: (recentChanges.window_days as number | null) ?? 0,
    items: ((recentChanges.items as Array<Record<string, unknown>> | undefined) ?? []).map(mapEntityTimelineClaim),
  };
}

function mapSourceAnalysis(analysis: Record<string, unknown>): SourceAnalysis {
  return {
    entities: ((analysis.entities as Array<Record<string, unknown>> | undefined) ?? []).map(mapSourceEntity),
    claims: ((analysis.claims as Array<Record<string, unknown>> | undefined) ?? []).map(mapSourceClaim),
  };
}

/**
 * Send a message to `/api/chat` and return the current JSON response.
 * Calls `onContent` with the full assistant reply.
 * Calls `onSources` with the accompanying source list.
 * Calls `onDone` after the response has been processed.
 */
export async function sendMessage(
  conversationId: string,
  message: string,
  onContent: (content: string) => void,
  onSources: (sources: Source[]) => void,
  onDone: () => void,
): Promise<void> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });

  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }

  const data = await res.json() as { content: string; sources: Array<Record<string, unknown>> };
  onContent(data.content);
  onSources((data.sources ?? []).map((source) => ({
    sourceId: (source.source_id as string | undefined) ?? undefined,
    title: source.title as string,
    url: (source.url as string | null) ?? null,
    author: (source.author as string | null) ?? null,
    score: source.score as number,
    publishedAt: (source.published_at as string | null) ?? null,
    kind: (source.kind as string | null) ?? null,
    tier: (source.tier as string | null) ?? null,
    publisher: (source.publisher as string | null) ?? null,
  })));
  onDone();
}

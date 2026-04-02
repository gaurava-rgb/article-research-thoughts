import type { Conversation, Insight, Message, RelatedConversation, Source } from "./types";

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

export async function fetchSimilarConversations(
  query: string,
  excludeId: string,
): Promise<RelatedConversation[]> {
  const params = new URLSearchParams({ query, exclude_id: excludeId });
  const res = await fetch(`${BASE}/api/conversations/similar?${params}`);
  if (!res.ok) return [];
  return res.json() as Promise<RelatedConversation[]>;
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

  const data = await res.json() as { content: string; sources: Source[] };
  onContent(data.content);
  onSources(data.sources ?? []);
  onDone();
}

import type { Conversation, Message, Source } from "./types";

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

/**
 * Send a message to /api/chat and stream the SSE response.
 * Calls onToken for each incremental text chunk.
 * Calls onSources once after all tokens arrive.
 * Calls onDone when the stream terminates.
 */
export async function sendMessage(
  conversationId: string,
  message: string,
  onToken: (token: string) => void,
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
  onToken(data.content);
  onSources(data.sources ?? []);
  onDone();
}

export interface Source {
  title: string;
  url: string;
  author: string;
  score: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[]; // Only present on assistant messages, after stream completes
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  createdAt: string;
  updatedAt: string;
}

// SSE event shapes from /api/chat
export type ChatEvent =
  | { type: "token"; content: string }
  | { type: "sources"; sources: Source[] };

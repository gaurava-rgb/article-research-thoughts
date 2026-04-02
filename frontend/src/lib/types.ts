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

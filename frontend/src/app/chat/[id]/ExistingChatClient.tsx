"use client";

import { useEffect, useState } from "react";
import { fetchMessages } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import type { Message } from "@/lib/types";

export function ExistingChatClient({ conversationId }: { conversationId: string }) {
  const [messages, setMessages] = useState<Message[] | null>(null);

  useEffect(() => {
    fetchMessages(conversationId).then(setMessages);
  }, [conversationId]);

  if (messages === null) {
    return <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Loading conversation...</div>;
  }

  return <ChatPanel conversationId={conversationId} initialMessages={messages} />;
}

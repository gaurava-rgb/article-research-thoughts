"use client";

import { useEffect, useState } from "react";
import { createConversation } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";

export function NewChatClient() {
  const [conversationId, setConversationId] = useState<string | null>(null);

  useEffect(() => {
    createConversation().then((conv) => setConversationId(conv.id));
  }, []);

  if (!conversationId) {
    return <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Starting conversation...</div>;
  }

  return <ChatPanel conversationId={conversationId} />;
}

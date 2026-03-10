"use client";

import { useEffect, useState } from "react";
import { createConversation } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import { IngestionPanel } from "@/components/IngestionPanel";

export function NewChatClient() {
  const [conversationId, setConversationId] = useState<string | null>(null);

  useEffect(() => {
    createConversation().then((conv) => setConversationId(conv.id));
  }, []);

  if (!conversationId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
        Starting conversation...
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <IngestionPanel />
      <div className="flex-1 overflow-hidden">
        <ChatPanel conversationId={conversationId} />
      </div>
    </div>
  );
}

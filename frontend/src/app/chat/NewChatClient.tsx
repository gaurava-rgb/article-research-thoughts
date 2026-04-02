"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { createConversation } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import { IngestionPanel } from "@/components/IngestionPanel";

export function NewChatClient() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    createConversation()
      .then((conv) => setConversationId(conv.id))
      .catch((err) => setError(String(err)));
  }, []);

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-4">
        <p className="text-center text-sm text-destructive">
          Couldn&apos;t start a new conversation.
        </p>
        <p className="text-center text-xs text-muted-foreground max-w-sm">
          {error}
        </p>
      </div>
    );
  }

  if (!conversationId) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
        <div className="text-center space-y-1">
          <p className="text-sm font-medium text-foreground">Setting up your chat</p>
          <p className="text-xs text-muted-foreground">One moment...</p>
        </div>
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

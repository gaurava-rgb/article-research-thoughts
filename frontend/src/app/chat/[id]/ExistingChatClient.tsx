"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { fetchMessages } from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import { IngestionPanel } from "@/components/IngestionPanel";
import type { Message } from "@/lib/types";

export function ExistingChatClient({ conversationId }: { conversationId: string }) {
  const [messages, setMessages] = useState<Message[] | null>(null);

  useEffect(() => {
    fetchMessages(conversationId).then(setMessages);
  }, [conversationId]);

  if (messages === null) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
        <div className="text-center space-y-1">
          <p className="text-sm font-medium text-foreground">Loading conversation</p>
          <p className="text-xs text-muted-foreground">Fetching your messages...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <IngestionPanel />
      <div className="flex-1 overflow-hidden">
        <ChatPanel conversationId={conversationId} initialMessages={messages} />
      </div>
    </div>
  );
}

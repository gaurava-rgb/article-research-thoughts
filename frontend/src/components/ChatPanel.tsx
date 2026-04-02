"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { MessageBubble } from "./MessageBubble";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { fetchSimilarConversations, sendMessage } from "@/lib/api";
import type { Message, RelatedConversation, Source } from "@/lib/types";

interface ChatPanelProps {
  conversationId: string;
  initialMessages?: Message[];
}

export function ChatPanel({ conversationId, initialMessages = [] }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isAwaitingResponse, setIsAwaitingResponse] = useState(false);
  const [relatedConversations, setRelatedConversations] = useState<RelatedConversation[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Track whether the first message has been sent in this session
  const isFirstMessageRef = useRef(initialMessages.length === 0);

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isAwaitingResponse) return;

    setInput("");
    setIsAwaitingResponse(true);

    // Optimistically add the user message
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    scrollToBottom();

    // Add a placeholder assistant message that is filled once the reply returns
    const assistantId = crypto.randomUUID();
    const placeholderMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, placeholderMsg]);

    const wasFirstMessage = isFirstMessageRef.current;
    if (wasFirstMessage) {
      isFirstMessageRef.current = false;
    }

    try {
      await sendMessage(
        conversationId,
        trimmed,
        (content) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content } : m,
            ),
          );
          scrollToBottom();
        },
        (sources: Source[]) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, sources } : m)),
          );
        },
        () => {
          setIsAwaitingResponse(false);
          scrollToBottom();
          // After the first message in a new conversation, surface related past convs
          if (wasFirstMessage) {
            fetchSimilarConversations(trimmed, conversationId)
              .then((similar) => {
                if (similar.length > 0) setRelatedConversations(similar);
              })
              .catch(() => {});
          }
        },
      );
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "Error: could not reach the backend. Is FastAPI running?" }
            : m,
        ),
      );
      setIsAwaitingResponse(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Message list */}
      <ScrollArea className="flex-1 px-4 py-4">
        <div className="mx-auto max-w-2xl space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center pt-20 pb-12 px-6 text-center">
              <p className="text-base font-medium text-foreground mb-1">
                What would you like to explore?
              </p>
              <p className="text-sm text-muted-foreground max-w-md">
                Ask anything about your saved articles. Your answers are grounded in what you&apos;ve read.
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isPending={isAwaitingResponse && msg.id === messages[messages.length - 1]?.id && msg.role === "assistant"}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Related conversations nudge (surfaces after first message only) */}
      {relatedConversations.length > 0 && (
        <div className="border-t bg-muted/30 px-4 py-2">
          <p className="mb-1 text-xs font-medium text-muted-foreground">
            You explored related topics before:
          </p>
          <div className="flex flex-wrap gap-2">
            {relatedConversations.map((c) => (
              <Link
                key={c.conversation_id}
                href={`/chat/${c.conversation_id}`}
                className="rounded-md border bg-background px-2 py-1 text-xs text-foreground transition-colors hover:bg-muted"
              >
                {c.title}
                <span className="ml-1 text-muted-foreground">({c.date})</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t bg-background px-4 py-3">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-2xl gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your saved reading..."
            rows={2}
            disabled={isAwaitingResponse}
            className="resize-none"
          />
          <Button type="submit" disabled={isAwaitingResponse || !input.trim()} className="self-end">
            {isAwaitingResponse ? "Thinking…" : "Send"}
          </Button>
        </form>
      </div>
    </div>
  );
}

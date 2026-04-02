"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, MessageSquare, Sparkles } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { fetchConversations, fetchInsights, markInsightSeen } from "@/lib/api";
import type { Conversation, Insight } from "@/lib/types";

interface ConvSidebarProps {
  currentConversationId?: string;
}

export function ConvSidebar({ currentConversationId }: ConvSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [unseenCount, setUnseenCount] = useState(0);
  const [insightsOpen, setInsightsOpen] = useState(false);
  const [expandedInsight, setExpandedInsight] = useState<string | null>(null);

  useEffect(() => {
    fetchConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchInsights()
      .then((data) => {
        setInsights(data.insights);
        setUnseenCount(data.unseen_count);
      })
      .catch(() => {});
  }, []);

  async function handleInsightClick(insight: Insight) {
    if (expandedInsight === insight.id) {
      setExpandedInsight(null);
      return;
    }
    setExpandedInsight(insight.id);
    if (!insight.seen) {
      try {
        await markInsightSeen(insight.id);
        setInsights((prev) =>
          prev.map((i) => (i.id === insight.id ? { ...i, seen: true } : i))
        );
        setUnseenCount((prev) => Math.max(0, prev - 1));
      } catch {
        // non-critical
      }
    }
  }

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-foreground truncate">Conversations</span>
          <SidebarTrigger className="shrink-0" />
        </div>
        <Link
          href="/chat"
          className="mt-3 flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <MessageSquare className="h-4 w-4" aria-hidden />
          New Chat
        </Link>
      </SidebarHeader>
      <SidebarContent>
        {/* Insights section */}
        <div className="border-b px-2 py-2">
          <button
            onClick={() => setInsightsOpen((prev) => !prev)}
            className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Sparkles className="h-4 w-4 shrink-0" aria-hidden />
            <span className="flex-1 text-left">Insights</span>
            {unseenCount > 0 && (
              <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold text-primary-foreground leading-none">
                {unseenCount}
              </span>
            )}
            {insightsOpen ? (
              <ChevronDown className="h-3 w-3 shrink-0" aria-hidden />
            ) : (
              <ChevronRight className="h-3 w-3 shrink-0" aria-hidden />
            )}
          </button>

          {insightsOpen && (
            <div className="mt-1 space-y-1 pb-1">
              {insights.length === 0 ? (
                <p className="px-3 py-3 text-xs text-muted-foreground">
                  No insights yet. Generate a weekly digest from the Add Sources panel.
                </p>
              ) : (
                insights.map((insight) => (
                  <div key={insight.id} className="rounded-md overflow-hidden">
                    <button
                      onClick={() => handleInsightClick(insight)}
                      className="flex w-full items-start gap-2 px-3 py-2 text-left transition-colors hover:bg-muted"
                    >
                      <span className="mt-0.5 shrink-0">
                        {insight.seen ? (
                          <span className="inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
                        ) : (
                          <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-1 text-xs font-medium text-foreground">
                          {insight.title}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {new Date(insight.createdAt).toLocaleDateString()}
                        </p>
                      </div>
                      {expandedInsight === insight.id ? (
                        <ChevronDown className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" aria-hidden />
                      ) : (
                        <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" aria-hidden />
                      )}
                    </button>
                    {expandedInsight === insight.id && (
                      <div className="mx-2 mb-2 rounded-md border bg-muted/40 p-3">
                        <p className="whitespace-pre-wrap text-xs text-foreground leading-relaxed">
                          {insight.body}
                        </p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Conversations list */}
        <SidebarMenu className="px-2 py-3">
          {conversations.length === 0 && (
            <div className="px-3 py-6 text-center">
              <p className="text-xs text-muted-foreground">
                Start a new chat to begin. Your conversations will appear here.
              </p>
            </div>
          )}
          {conversations.map((conv) => (
            <SidebarMenuItem key={conv.id}>
              <SidebarMenuButton
                asChild
                isActive={conv.id === currentConversationId}
              >
                <Link href={`/chat/${conv.id}`} className="flex flex-col items-start gap-0.5 py-2.5 px-3">
                  <span className="line-clamp-1 text-sm">
                    {conv.title ?? "Untitled conversation"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(conv.updatedAt).toLocaleDateString()}
                  </span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
    </Sidebar>
  );
}

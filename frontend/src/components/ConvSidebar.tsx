"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, FileSearch, MessageSquare, Sparkles } from "lucide-react";
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

  const loadInsights = () => {
    fetchInsights()
      .then((data) => {
        setInsights(data.insights);
        setUnseenCount(data.unseen_count);
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadInsights();
    const handler = () => loadInsights();
    window.addEventListener("insights:refresh", handler);
    return () => window.removeEventListener("insights:refresh", handler);
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

  function renderInsightTypeLabel(type: Insight["type"]): string {
    switch (type) {
      case "coverage_gap":
        return "Coverage gap";
      case "counterpoint":
        return "Counterpoint";
      case "follow_up":
        return "Follow-up";
      case "watch":
        return "Watch";
      case "contradiction":
        return "Contradiction";
      case "pattern":
        return "Pattern";
      default:
        return "Digest";
    }
  }

  function renderInsightTypeClass(type: Insight["type"]): string {
    switch (type) {
      case "coverage_gap":
        return "border-amber-300/30 bg-amber-500/10 text-amber-100";
      case "counterpoint":
        return "border-rose-300/30 bg-rose-500/10 text-rose-100";
      case "follow_up":
        return "border-sky-300/30 bg-sky-500/10 text-sky-100";
      case "watch":
        return "border-emerald-300/30 bg-emerald-500/10 text-emerald-100";
      default:
        return "border-white/10 bg-white/5 text-muted-foreground";
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
        <Link
          href="/entities"
          className="mt-2 flex items-center justify-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          <FileSearch className="h-4 w-4" aria-hidden />
          Entity Workbench
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
                  No insights yet. Generate a digest or research follow-ups from the Add Sources panel.
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
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${renderInsightTypeClass(insight.type)}`}>
                            {renderInsightTypeLabel(insight.type)}
                          </span>
                          {insight.entities.slice(0, 2).map((entity) => (
                            <span
                              key={entity.id}
                              className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-muted-foreground"
                            >
                              {entity.canonicalName}
                            </span>
                          ))}
                        </div>
                        {insight.summary && (
                          <p className="mb-2 text-xs font-medium text-foreground">
                            {insight.summary}
                          </p>
                        )}
                        <p className="whitespace-pre-wrap text-xs text-foreground leading-relaxed">
                          {insight.body}
                        </p>
                        {typeof insight.metadata.reason === "string" && (
                          <p className="mt-2 text-[11px] text-muted-foreground">
                            Why shown: {insight.metadata.reason}
                          </p>
                        )}
                        {typeof insight.metadata.query === "string" && (
                          <p className="mt-2 rounded-md border border-dashed border-white/10 bg-background/60 px-2 py-1 text-[11px] text-muted-foreground">
                            Suggested query: <span className="text-foreground">{insight.metadata.query}</span>
                          </p>
                        )}
                        {insight.claims.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {insight.claims.slice(0, 2).map((claim) => (
                              <p key={claim.id} className="text-[11px] text-muted-foreground">
                                Trigger: {claim.claimText}
                              </p>
                            ))}
                          </div>
                        )}
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

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { fetchConversations } from "@/lib/api";
import type { Conversation } from "@/lib/types";

interface ConvSidebarProps {
  currentConversationId?: string;
}

export function ConvSidebar({ currentConversationId }: ConvSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    fetchConversations()
      .then(setConversations)
      .catch(() => {
        // Sidebar is non-critical; swallow errors gracefully
      });
  }, []);

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-muted-foreground">Past Conversations</span>
          <SidebarTrigger />
        </div>
        <Link
          href="/chat"
          className="mt-2 block rounded-md bg-primary px-3 py-1.5 text-center text-xs font-medium text-primary-foreground hover:bg-primary/90"
        >
          + New Chat
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {conversations.length === 0 && (
            <p className="px-4 py-2 text-xs text-muted-foreground">No past conversations yet.</p>
          )}
          {conversations.map((conv) => (
            <SidebarMenuItem key={conv.id}>
              <SidebarMenuButton
                asChild
                isActive={conv.id === currentConversationId}
              >
                <Link href={`/chat/${conv.id}`} className="flex flex-col items-start gap-0.5 py-2">
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

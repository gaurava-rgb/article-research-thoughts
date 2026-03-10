"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Source } from "@/lib/types";

interface CitationCardProps {
  source: Source;
  index: number;
}

export function CitationCard({ source, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      className="mt-1 cursor-pointer border-l-4 border-l-blue-400 text-sm transition-colors hover:bg-muted/50"
      onClick={() => setExpanded((prev) => !prev)}
    >
      <CardHeader className="p-2 pb-0">
        <div className="flex items-start justify-between gap-2">
          <span className="font-medium leading-tight text-blue-700 dark:text-blue-400">
            [{index + 1}] {source.title}
          </span>
          <span className="shrink-0 text-xs text-muted-foreground">{expanded ? "▲" : "▼"}</span>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="p-2 pt-1">
          {source.author && (
            <p className="text-xs text-muted-foreground">by {source.author}</p>
          )}
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="mt-1 block text-xs text-blue-600 underline hover:text-blue-800"
          >
            Open original article →
          </a>
          <p className="mt-1 text-xs text-muted-foreground">
            Relevance score: {(source.score * 100).toFixed(0)}%
          </p>
        </CardContent>
      )}
    </Card>
  );
}

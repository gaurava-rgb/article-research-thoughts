import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CitationCard } from "./CitationCard";
import type { Message } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
  isPending?: boolean;
}

// Memoized markdown renderer to avoid re-rendering unchanged message content.
const MemoizedMarkdown = memo(({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      // Open all links in new tabs
      a: ({ ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
    }}
  >
    {content}
  </ReactMarkdown>
));
MemoizedMarkdown.displayName = "MemoizedMarkdown";

/**
 * Split assistant content into [FROM YOUR SOURCES], [ANALYSIS], and [CONTRADICTIONS] sections.
 * Returns an array of { label, text } objects for distinct visual styling.
 */
function parseAssistantSections(content: string): Array<{ label: string | null; text: string }> {
  const SOURCES_MARKER = "[FROM YOUR SOURCES]";
  const ANALYSIS_MARKER = "[ANALYSIS]";
  const CONTRADICTIONS_MARKER = "[CONTRADICTIONS]";

  // Collect all marker positions
  const markers: Array<{ idx: number; label: string; markerLen: number }> = [];
  const s = content.indexOf(SOURCES_MARKER);
  const a = content.indexOf(ANALYSIS_MARKER);
  const c = content.indexOf(CONTRADICTIONS_MARKER);
  if (s !== -1) markers.push({ idx: s, label: "FROM YOUR SOURCES", markerLen: SOURCES_MARKER.length });
  if (a !== -1) markers.push({ idx: a, label: "ANALYSIS", markerLen: ANALYSIS_MARKER.length });
  if (c !== -1) markers.push({ idx: c, label: "CONTRADICTIONS", markerLen: CONTRADICTIONS_MARKER.length });

  if (markers.length === 0) return [{ label: null, text: content }];

  markers.sort((a, b) => a.idx - b.idx);

  const sections: Array<{ label: string | null; text: string }> = [];

  // Text before first marker
  if (markers[0].idx > 0) {
    sections.push({ label: null, text: content.slice(0, markers[0].idx).trim() });
  }

  for (let i = 0; i < markers.length; i++) {
    const start = markers[i].idx + markers[i].markerLen;
    const end = i + 1 < markers.length ? markers[i + 1].idx : content.length;
    const text = content.slice(start, end).trim();
    if (text) sections.push({ label: markers[i].label, text });
  }

  return sections;
}

export function MessageBubble({ message, isPending = false }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl bg-blue-600 px-4 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant message: parse sections, render with distinct styling
  const sections = parseAssistantSections(message.content);

  return (
    <div className="flex flex-col gap-2">
      <div className="max-w-[85%] rounded-2xl bg-zinc-800 px-4 py-3 text-sm text-zinc-100">
        {sections.map((section, i) => {
          if (section.label === "FROM YOUR SOURCES") {
            return (
              <div key={i} className="mb-3 rounded-lg border border-blue-500/40 bg-blue-500/10 p-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-blue-400">
                  From Your Sources
                </p>
                <div className="prose prose-sm max-w-none prose-invert text-foreground">
                  <MemoizedMarkdown content={section.text} />
                </div>
              </div>
            );
          }
          if (section.label === "ANALYSIS") {
            return (
              <div key={i} className="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-400">
                  Analysis
                </p>
                <div className="prose prose-sm max-w-none prose-invert text-foreground">
                  <MemoizedMarkdown content={section.text} />
                </div>
              </div>
            );
          }
          if (section.label === "CONTRADICTIONS") {
            return (
              <div key={i} className="mb-3 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-rose-400">
                  Contradictions
                </p>
                <div className="prose prose-sm max-w-none prose-invert text-foreground">
                  <MemoizedMarkdown content={section.text} />
                </div>
              </div>
            );
          }
          return (
            <div key={i} className="prose prose-sm max-w-none prose-invert text-foreground">
              <MemoizedMarkdown content={section.text} />
            </div>
          );
        })}
        {isPending && (
          <span className="inline-block h-4 w-1 animate-pulse bg-current opacity-70" />
        )}
      </div>

      {/* Citation cards below the message (UI-02) */}
      {message.sources && message.sources.length > 0 && (
        <div className="ml-1 max-w-[85%] space-y-1">
          {message.sources.map((source, i) => (
            <CitationCard key={i} source={source} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CitationCard } from "./CitationCard";
import type { Message } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

// Memoized markdown renderer — prevents re-render thrash during token streaming
// (see Research pitfall 2: react-markdown re-renders on every state update)
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
 * Split assistant content into [FROM YOUR SOURCES] and [ANALYSIS] sections.
 * Returns an array of { label, content } objects for distinct visual styling.
 */
function parseAssistantSections(content: string): Array<{ label: string | null; text: string }> {
  // Markers injected by the SYSTEM_PROMPT in router.py
  const SOURCES_MARKER = "[FROM YOUR SOURCES]";
  const ANALYSIS_MARKER = "[ANALYSIS]";

  const sections: Array<{ label: string | null; text: string }> = [];
  const remaining = content;

  const sourcesIdx = remaining.indexOf(SOURCES_MARKER);
  const analysisIdx = remaining.indexOf(ANALYSIS_MARKER);

  if (sourcesIdx === -1 && analysisIdx === -1) {
    // No section markers — render as a single plain block
    return [{ label: null, text: remaining }];
  }

  // Text before first marker (if any)
  const firstMarker = Math.min(
    sourcesIdx !== -1 ? sourcesIdx : Infinity,
    analysisIdx !== -1 ? analysisIdx : Infinity,
  );
  if (firstMarker > 0) {
    sections.push({ label: null, text: remaining.slice(0, firstMarker).trim() });
  }

  // Extract SOURCES section
  if (sourcesIdx !== -1) {
    const afterSources = sourcesIdx + SOURCES_MARKER.length;
    const nextSection = analysisIdx > sourcesIdx ? analysisIdx : remaining.length;
    sections.push({
      label: "FROM YOUR SOURCES",
      text: remaining.slice(afterSources, nextSection).trim(),
    });
  }

  // Extract ANALYSIS section
  if (analysisIdx !== -1) {
    const afterAnalysis = analysisIdx + ANALYSIS_MARKER.length;
    sections.push({
      label: "ANALYSIS",
      text: remaining.slice(afterAnalysis).trim(),
    });
  }

  return sections;
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
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
          return (
            <div key={i} className="prose prose-sm max-w-none prose-invert text-foreground">
              <MemoizedMarkdown content={section.text} />
            </div>
          );
        })}
        {isStreaming && (
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

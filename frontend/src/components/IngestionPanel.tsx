"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { generateDigest } from "@/lib/api";

type SyncState = "idle" | "running" | "complete" | "warning" | "error";
type DigestState = "idle" | "running" | "complete" | "no_articles" | "error";

export function IngestionPanel() {
  const [open, setOpen] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [syncMessage, setSyncMessage] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [urlMessage, setUrlMessage] = useState("");
  const [digestState, setDigestState] = useState<DigestState>("idle");
  const [digestMessage, setDigestMessage] = useState("");

  async function handleSync() {
    setSyncState("running");
    setSyncMessage(
      "Starting Readwise sync. Large libraries can outlast this browser request."
    );
    try {
      const res = await fetch("/api/sync", { method: "POST" });
      const data = (await res.json()) as { status?: string; message?: string };

      if (!res.ok) {
        setSyncState("error");
        setSyncMessage(data.message ?? `Sync request failed (${res.status}).`);
        return;
      }

      if (data.status === "complete") {
        setSyncState("complete");
        setSyncMessage(data.message ?? "Sync request completed.");
        return;
      }

      setSyncState("warning");
      setSyncMessage(
        data.message ??
          "Sync finished without a clear final status. It may be safest to check again before assuming it failed."
      );
    } catch {
      setSyncState("warning");
      setSyncMessage(
        "This browser request ended before sync reported a final result. On long runs, the backend may still be working. Wait a bit, then run sync again if needed."
      );
    }
  }

  async function handleGenerateDigest() {
    setDigestState("running");
    setDigestMessage("Generating weekly digest…");
    try {
      const data = await generateDigest();
      if (data.status === "no_articles") {
        setDigestState("no_articles");
        setDigestMessage("No articles ingested in the last 7 days.");
      } else {
        setDigestState("complete");
        setDigestMessage("Digest generated! Open Insights in the sidebar to read it.");
      }
    } catch {
      setDigestState("error");
      setDigestMessage("Failed to generate digest. Is the backend running?");
    }
  }

  function handleAddUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!urlInput.trim()) return;
    // URL ingestion pipeline is out of scope for Phase 2.
    setUrlMessage("Add by URL is coming soon. Use Readwise sync to add articles now.");
    setUrlInput("");
  }

  return (
    <div className="border-b bg-muted/30">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <span className="text-muted-foreground/70" aria-hidden>
          {open ? "▼" : "▶"}
        </span>
        <span>Add sources</span>
      </button>

      {/* Expanded panel */}
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-4">
          {/* Readwise sync */}
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground">Readwise Sync</p>
            <p className="mb-2 text-xs text-muted-foreground">
              Large libraries can take longer than one browser request. If this request ends
              early, backend sync work may still continue.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSync}
              disabled={syncState === "running"}
            >
              {syncState === "running" ? "Waiting on sync request…" : "Sync Readwise Articles"}
            </Button>
            {syncMessage && (
              <p
                className={`mt-1 text-xs ${
                  syncState === "error"
                    ? "text-red-600"
                    : syncState === "warning"
                      ? "text-amber-600"
                      : syncState === "complete"
                        ? "text-green-600"
                        : "text-muted-foreground"
                }`}
              >
                {syncMessage}
              </p>
            )}
          </div>

          <Separator />

          {/* Weekly digest */}
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground">Weekly Digest</p>
            <p className="mb-2 text-xs text-muted-foreground">
              Summarizes what you&apos;ve been reading this week by theme.
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerateDigest}
              disabled={digestState === "running"}
            >
              {digestState === "running" ? "Generating…" : "Generate Digest"}
            </Button>
            {digestMessage && (
              <p
                className={`mt-1 text-xs ${
                  digestState === "error"
                    ? "text-red-600"
                    : digestState === "complete"
                      ? "text-green-600"
                      : "text-muted-foreground"
                }`}
              >
                {digestMessage}
              </p>
            )}
          </div>

          <Separator />

          {/* URL ingestion (coming soon) */}
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground">
              Add by URL <span className="font-normal text-muted-foreground/80">(coming soon)</span>
            </p>
            <form onSubmit={handleAddUrl} className="flex gap-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="Paste article URL…"
                className="flex-1 rounded-md border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <Button type="submit" size="sm" variant="outline">
                Add URL
              </Button>
            </form>
            {urlMessage && (
              <p className="mt-1 text-xs text-muted-foreground">{urlMessage}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

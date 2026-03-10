"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

type SyncState = "idle" | "running" | "complete" | "error";

export function IngestionPanel() {
  const [open, setOpen] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [syncMessage, setSyncMessage] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [urlMessage, setUrlMessage] = useState("");

  async function handleSync() {
    setSyncState("running");
    setSyncMessage("Syncing Readwise articles… this may take up to a minute.");
    try {
      const res = await fetch("/api/sync", { method: "POST" });
      const data = (await res.json()) as { status: string; message: string };
      setSyncState(data.status === "complete" ? "complete" : "error");
      setSyncMessage(data.message);
    } catch {
      setSyncState("error");
      setSyncMessage("Could not reach the backend. Is FastAPI running?");
    }
  }

  function handleAddUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!urlInput.trim()) return;
    // URL ingestion pipeline is out of scope for Phase 2.
    // This UI element satisfies UI-05's paste-URL spec at the front-end level.
    setUrlMessage("URL ingestion is not yet implemented. Use Readwise sync to add articles.");
    setUrlInput("");
  }

  return (
    <div className="border-b bg-muted/30">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span>{open ? "▼" : "▶"}</span>
        <span>Add Sources</span>
      </button>

      {/* Expanded panel */}
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-4">
          {/* Readwise sync */}
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground">Readwise Sync</p>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSync}
              disabled={syncState === "running"}
            >
              {syncState === "running" ? "Syncing…" : "Sync Readwise Articles"}
            </Button>
            {syncMessage && (
              <p
                className={`mt-1 text-xs ${
                  syncState === "error" ? "text-red-600" : "text-green-600"
                }`}
              >
                {syncMessage}
              </p>
            )}
          </div>

          <Separator />

          {/* URL ingestion (UI placeholder) */}
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground">Add by URL</p>
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

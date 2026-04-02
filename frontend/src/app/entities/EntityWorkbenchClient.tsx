"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useState } from "react";
import { ArrowRight, FileSearch, Loader2, Search } from "lucide-react";
import { fetchEntityDirectory } from "@/lib/api";
import type { EntityDirectoryItem } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

function formatDate(value: string | null): string {
  if (!value) return "No dated activity";
  return new Date(value).toLocaleDateString();
}

export function EntityWorkbenchClient() {
  const [entities, setEntities] = useState<EntityDirectoryItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    fetchEntityDirectory()
      .then(setEntities)
      .catch((err) => setError(String(err)));
  }, []);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center px-6">
        <div className="max-w-md rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-center">
          <p className="text-sm font-semibold text-rose-300">Couldn&apos;t load the entity workbench.</p>
          <p className="mt-2 text-sm text-rose-100/90">{error}</p>
        </div>
      </div>
    );
  }

  if (entities === null) {
    return (
      <div className="flex h-full items-center justify-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
        <p className="text-sm text-muted-foreground">Loading entity dossiers…</p>
      </div>
    );
  }

  const filteredEntities = deferredQuery
    ? entities.filter((entity) => {
        const haystack = [
          entity.canonicalName,
          entity.entityType,
          entity.ticker ?? "",
          entity.latestClaimText ?? "",
          ...entity.aliases,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(deferredQuery);
      })
    : entities;

  return (
    <div className="min-h-full overflow-y-auto bg-[radial-gradient(circle_at_top,_rgba(245,158,11,0.14),_transparent_28%),linear-gradient(180deg,_rgba(15,23,42,0.98),_rgba(15,23,42,1))] text-slate-50">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-8 lg:px-10">
        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/20 backdrop-blur">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-amber-200/80">
                Analyst Workbench
              </p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">
                Entity dossiers built from stored claims
              </h1>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Browse companies, products, and markets as inspectable timelines. Each dossier is
                grounded in stored evidence, not a fresh chat reconstruction.
              </p>
            </div>
            <div className="w-full max-w-md">
              <label className="mb-2 block text-xs font-medium uppercase tracking-[0.24em] text-slate-400">
                Filter Entities
              </label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search Acme, Atlas, competitor, market…"
                  className="border-white/10 bg-slate-950/60 pl-9 text-slate-50 placeholder:text-slate-500"
                />
              </div>
            </div>
          </div>
        </section>

        {filteredEntities.length === 0 ? (
          <section className="rounded-[2rem] border border-dashed border-white/15 bg-white/5 px-6 py-12 text-center">
            <FileSearch className="mx-auto h-8 w-8 text-slate-500" aria-hidden />
            <p className="mt-4 text-lg font-medium text-white">No dossiers match this filter.</p>
            <p className="mt-2 text-sm text-slate-400">
              Analyze a source first, or clear the search to see every stored entity dossier.
            </p>
          </section>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredEntities.map((entity) => (
              <Link
                key={entity.id}
                href={`/entities/${entity.id}`}
                className="group rounded-[1.75rem] border border-white/10 bg-white/5 p-5 transition-transform duration-200 hover:-translate-y-0.5 hover:border-amber-300/40 hover:bg-white/10"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                      {entity.entityType}
                    </p>
                    <h2 className="mt-2 text-xl font-semibold text-white">{entity.canonicalName}</h2>
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-0.5 group-hover:text-amber-200" aria-hidden />
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {entity.ticker && (
                    <Badge variant="outline" className="border-amber-300/30 bg-amber-300/10 text-amber-100">
                      {entity.ticker}
                    </Badge>
                  )}
                  <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-200">
                    {entity.claimCount} claims
                  </Badge>
                  <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-200">
                    {entity.sourceCount} sources
                  </Badge>
                </div>

                {entity.aliasCount > 0 && (
                  <p className="mt-4 text-xs text-slate-400">
                    Also seen as: {entity.aliases.slice(0, 3).join(", ")}
                  </p>
                )}

                <div className="mt-5 rounded-2xl border border-white/8 bg-slate-950/45 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    Latest tracked change
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-200">
                    {entity.latestClaimText ?? "No recent claim summary stored yet."}
                  </p>
                  <p className="mt-3 text-xs text-slate-500">{formatDate(entity.latestTimelineAt)}</p>
                </div>
              </Link>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}

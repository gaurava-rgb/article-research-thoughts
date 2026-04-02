"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Network,
  Quote,
  ScrollText,
  Sparkles,
} from "lucide-react";
import { fetchEntityDossier } from "@/lib/api";
import type { EntityDossier, EntityTimelineClaim } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

function formatDate(value: string | null): string {
  if (!value) return "Undated";
  return new Date(value).toLocaleDateString();
}

function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

function ClaimCard({ claim }: { claim: EntityTimelineClaim }) {
  return (
    <article className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-100">
              {humanize(claim.claim_type)}
            </Badge>
            <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-300">
              {humanize(claim.modality)}
            </Badge>
            {claim.stance && (
              <Badge
                variant="outline"
                className={
                  claim.stance === "negative"
                    ? "border-rose-300/30 bg-rose-400/10 text-rose-100"
                    : claim.stance === "positive"
                      ? "border-emerald-300/30 bg-emerald-400/10 text-emerald-100"
                      : "border-slate-300/20 bg-slate-400/10 text-slate-200"
                }
              >
                {claim.stance}
              </Badge>
            )}
            {claim.isContradictory && (
              <Badge variant="outline" className="border-amber-300/30 bg-amber-300/10 text-amber-100">
                {claim.contradictionCount} contradiction{claim.contradictionCount === 1 ? "" : "s"}
              </Badge>
            )}
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              {formatDate(claim.timelineAt)} · {claim.entityRole === "object" ? "Mentioned as affected entity" : "Primary entity claim"}
            </p>
            <h3 className="mt-2 text-lg font-semibold text-white">{claim.claim_text}</h3>
          </div>

          {(claim.subject_entity || claim.object_entity || claim.counterpartyEntity) && (
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
              {claim.subject_entity && (
                <Link href={`/entities/${claim.subject_entity.id}`} className="rounded-full border border-white/10 px-3 py-1 hover:border-amber-200/40 hover:text-white">
                  {claim.subject_entity.canonical_name}
                </Link>
              )}
              {claim.object_entity && (
                <Link href={`/entities/${claim.object_entity.id}`} className="rounded-full border border-white/10 px-3 py-1 hover:border-amber-200/40 hover:text-white">
                  {claim.object_entity.canonical_name}
                </Link>
              )}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3 text-sm text-slate-300 lg:min-w-[14rem]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            Source
          </p>
          <p className="mt-2 font-medium text-white">{claim.source.title ?? "Unknown source"}</p>
          <p className="mt-1 text-xs text-slate-500">{formatDate(claim.source.publishedAt ?? claim.source.ingestedAt)}</p>
          {claim.source.url && (
            <a
              href={claim.source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1 text-xs text-amber-200 hover:text-amber-100"
            >
              Open source
              <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          )}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <details className="group rounded-2xl border border-white/8 bg-slate-950/40 p-4">
          <summary className="cursor-pointer list-none text-sm font-medium text-white">
            Why is this here?
          </summary>
          <div className="mt-4 space-y-4">
            <div>
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                <Quote className="h-3.5 w-3.5" aria-hidden />
                Evidence
              </p>
              <div className="mt-3 space-y-2">
                {claim.evidence.length === 0 ? (
                  <p className="text-sm text-slate-400">No stored evidence quotes yet.</p>
                ) : (
                  claim.evidence.map((evidence) => (
                    <blockquote key={evidence.id} className="rounded-xl border border-white/8 bg-white/5 px-4 py-3 text-sm leading-6 text-slate-200">
                      “{evidence.evidence_text ?? "Stored evidence"}”
                    </blockquote>
                  ))
                )}
              </div>
            </div>

            {claim.links.length > 0 && (
              <div>
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                  <Network className="h-3.5 w-3.5" aria-hidden />
                  Linked Claims
                </p>
                <div className="mt-3 space-y-2">
                  {claim.links.map((link) => (
                    <div key={link.id} className="rounded-xl border border-white/8 bg-white/5 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                        {link.direction} · {humanize(link.linkType)}
                      </p>
                      <p className="mt-2 text-sm text-slate-100">
                        {link.relatedClaimText ?? "Linked claim"}
                      </p>
                      {link.explanation && (
                        <p className="mt-2 text-sm text-slate-400">{link.explanation}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </details>

        <div className="rounded-2xl border border-white/8 bg-slate-950/40 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            Analytical Lenses
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {claim.lenses.length === 0 ? (
              <p className="text-sm text-slate-400">No stored lens tags.</p>
            ) : (
              claim.lenses.map((lens) => (
                <Badge key={lens.id} variant="outline" className="border-white/10 bg-white/5 text-slate-200">
                  {lens.name}
                </Badge>
              ))
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

export function EntityDossierClient({ entityId }: { entityId: string }) {
  const [dossier, setDossier] = useState<EntityDossier | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEntityDossier(entityId)
      .then(setDossier)
      .catch((err) => setError(String(err)));
  }, [entityId]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center px-6">
        <div className="max-w-md rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-center">
          <p className="text-sm font-semibold text-rose-300">Couldn&apos;t load this dossier.</p>
          <p className="mt-2 text-sm text-rose-100/90">{error}</p>
        </div>
      </div>
    );
  }

  if (dossier === null) {
    return (
      <div className="flex h-full items-center justify-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden />
        <p className="text-sm text-muted-foreground">Loading dossier…</p>
      </div>
    );
  }

  return (
    <div className="min-h-full overflow-y-auto bg-[radial-gradient(circle_at_top_right,_rgba(16,185,129,0.16),_transparent_25%),radial-gradient(circle_at_top_left,_rgba(245,158,11,0.14),_transparent_22%),linear-gradient(180deg,_rgba(2,6,23,0.98),_rgba(15,23,42,1))] text-slate-50">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-5 rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/20 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link href="/entities" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Back to entity directory
              </Link>
              <p className="mt-4 text-xs font-semibold uppercase tracking-[0.3em] text-emerald-200/80">
                Entity Dossier
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white">
                {dossier.entity.canonical_name}
              </h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-100">
                {humanize(dossier.entity.entity_type)}
              </Badge>
              {dossier.entity.ticker && (
                <Badge variant="outline" className="border-emerald-300/30 bg-emerald-400/10 text-emerald-100">
                  {dossier.entity.ticker}
                </Badge>
              )}
              <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-100">
                {dossier.currentThesis.claimCount} claims
              </Badge>
              <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-100">
                {dossier.currentThesis.sourceCount} sources
              </Badge>
            </div>
          </div>

          {dossier.entity.aliases.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {dossier.entity.aliases.map((alias) => (
                <Badge key={alias.alias} variant="outline" className="border-white/10 bg-white/5 text-slate-300">
                  {alias.alias}
                </Badge>
              ))}
            </div>
          )}

          <p className="max-w-4xl text-sm leading-7 text-slate-300">{dossier.currentThesis.summary}</p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-6">
            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                  <Sparkles className="h-3.5 w-3.5" aria-hidden />
                  What Changed Recently
                </p>
                <p className="mt-3 text-sm leading-6 text-slate-300">{dossier.recentChanges.summary}</p>
                <div className="mt-4 space-y-3">
                  {dossier.recentChanges.items.map((claim) => (
                    <div key={claim.id} className="rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                        {formatDate(claim.timelineAt)}
                      </p>
                      <p className="mt-2 text-sm text-slate-100">{claim.claim_text}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                  <ScrollText className="h-3.5 w-3.5" aria-hidden />
                  Current Thesis
                </p>
                <div className="mt-4 space-y-3">
                  {dossier.currentThesis.topClaims.map((claim) => (
                    <div key={claim.id} className="rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                        {humanize(claim.claim_type)}
                      </p>
                      <p className="mt-2 text-sm text-slate-100">{claim.claim_text}</p>
                    </div>
                  ))}
                </div>
                {dossier.currentThesis.dominantLenses.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {dossier.currentThesis.dominantLenses.map((lens) => (
                      <Badge key={lens.name} variant="outline" className="border-white/10 bg-white/5 text-slate-200">
                        {lens.name} · {lens.count}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Timeline</p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">Stored claims, ordered by real dates</h2>
                </div>
              </div>
              {dossier.timeline.length === 0 ? (
                <div className="rounded-[1.75rem] border border-dashed border-white/15 bg-white/5 px-6 py-12 text-center">
                  <p className="text-lg font-medium text-white">No claims stored for this entity yet.</p>
                  <p className="mt-2 text-sm text-slate-400">
                    Run source analysis first, then return here to inspect the dossier.
                  </p>
                </div>
              ) : (
                dossier.timeline.map((claim) => <ClaimCard key={claim.id} claim={claim} />)
              )}
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                <Network className="h-3.5 w-3.5" aria-hidden />
                Relationships
              </p>
              {dossier.relationships.length === 0 ? (
                <p className="mt-4 text-sm text-slate-400">No structured relationships stored yet.</p>
              ) : (
                <div className="mt-4 space-y-4">
                  {dossier.relationships.map((group) => (
                    <div key={group.relationType}>
                      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                        {group.label}
                      </p>
                      <div className="mt-2 space-y-2">
                        {group.items.map((item) => (
                          <div key={item.id} className="rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3">
                            <div className="flex items-center justify-between gap-2">
                              {item.counterpartyEntity ? (
                                <Link
                                  href={`/entities/${item.counterpartyEntity.id}`}
                                  className="text-sm font-medium text-white hover:text-amber-200"
                                >
                                  {item.counterpartyEntity.canonical_name}
                                </Link>
                              ) : (
                                <p className="text-sm font-medium text-white">Unknown entity</p>
                              )}
                              <Badge variant="outline" className="border-white/10 bg-white/5 text-slate-300">
                                {item.direction}
                              </Badge>
                            </div>
                            {item.source?.title && (
                              <p className="mt-2 text-xs text-slate-500">{item.source.title}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

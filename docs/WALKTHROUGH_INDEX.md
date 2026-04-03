# Walkthrough Progress — Index of All Layer Files

## Last Updated: 2026-04-03

## Complete File Inventory

| File | Layer | What It Covers |
|------|-------|---------------|
| `layer1.md` | V1 Pipeline | Readwise -> sources -> chunks -> search -> answer + the build decision to layer on top |
| `layer2.md` | Extraction Pipeline | The 5 extraction outputs: entities, claims, evidence, claim links, lenses |
| `layer2a.md` | Multi-Entity Extraction | How one article fans out into many entities and claims across articles |
| `layer2b.md` | Entity Dedup | Exact-name dedup mechanism, known fuzzy matching gap (PARKED for later) |
| `layer3.md` | Surfaces | The 4 UI surfaces: chat, entity workbench, insights sidebar, ingestion panel |
| `layer4.md` | LightRAG Sidecar | Architecture, sidecar principle, what it gives you, two pieces to build |
| `layer4-layman.md` | LightRAG (Layman) | Corkboard analogy, 3 embedding types explained, retrieval modes with examples |
| `layer4b.md` | Embeddings Question | Why LightRAG can't reuse Supabase embeddings (4 blockers + cost analysis) |
| `layer5.md` | Full Combined View | Everything connected in one diagram + data flow summary + dependency map + authority model |
| `layer6.md` | Deployment Architecture | What runs where, what's working/broken/missing, deploy sequence, traceability checklist |
| `layer6a.md` | V2 Deploy Log | Step-by-step record of what was done to deploy the analyst workbench to production |

## Reading Order

**For understanding the system:**
1. `layer1.md` — Start here. Understand V1 and why it wasn't enough.
2. `layer2.md` — The extraction pipeline that makes V2 different.
3. `layer2a.md` — How extraction works across articles (multi-entity).
4. `layer3.md` — What the user actually sees (the 4 surfaces).
5. `layer5.md` — The full picture in one diagram.

**For understanding LightRAG:**
6. `layer4.md` — Technical architecture of the sidecar.
7. `layer4-layman.md` — Same thing but with analogies and examples.
8. `layer4b.md` — Why embeddings can't be shared.

**For deployment/ops:**
9. `layer6.md` — Where everything runs, what's working, known issues.
10. `layer6a.md` — Deploy log of what was actually done.

**Parked items:**
- `layer2b.md` — Fuzzy entity dedup (not built, noted for later).

## Current State of the System (as of 2026-04-03)

- **V1 pipeline:** ✅ Live on Vercel (Readwise sync, chunking, hybrid search, chat)
- **V2 analyst workbench:** ✅ Live (entities, claims, dossiers, suggestions endpoints)
- **All routes working:** ✅ Static + dynamic (`/entities/[id]`, `/chat/[id]` fixed)
- **GitHub repo:** ✅ https://github.com/gaurava-rgb/article-research-thoughts (public)
- **LightRAG sidecar:** 🔴 Not built (documentation only, needs VPS + Docker + code)
- **Bulk extraction:** ⚠️ Only ~1 source analyzed. Need to run extraction on remaining sources.

## Known Issues / Gotchas

- **Vercel ↔ GitHub NOT auto-connected.** Deploys are manual: `vercel --prod --yes`
- **GitHub repo must stay public** for Vercel Hobby plan to accept deploys
- **Debug exception handler exposed** in `api/index.py` (shows stack traces in prod)
- **No auth** on any endpoint

## What's Next

1. Run extraction on more/all sources to populate entity workbench
2. Generate first insights and suggestions
3. Set up LightRAG on VPS (Docker + sync adapter + retrieval toggle)
4. Address security issues (auth, debug handler, rate limiting)

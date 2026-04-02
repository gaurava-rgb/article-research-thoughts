# Sprint 4 — Synthesis Engine

**Goal:** User asks a complex question and receives a narrative synthesis across multiple sources — not a list of excerpts — with contradictions surfaced explicitly.
**Phase:** 04
**Started:** 2026-04-01
**Status:** COMPLETE — verified 2026-04-01

---

## Current State (verified 2026-04-01)

| Item | Status | Notes |
|------|--------|-------|
| `[FROM YOUR SOURCES]` / `[ANALYSIS]` section parsing | DONE | MessageBubble.tsx already parses and styles these |
| CitationCard component | DONE | Shown below each assistant message |
| Links open in new tab | DONE | MessageBubble.tsx `<a target="_blank">` |
| `[CONTRADICTIONS]` section | TODO | Not parsed in frontend, not emitted by backend |
| Synthesis system prompt | WEAK | Current prompt asks for sections but doesn't enforce narrative synthesis or contradiction detection |
| Sources per query | TODO | Currently top_k=5; Phase 4 needs 10 for meaningful synthesis |
| Test coverage for chat endpoint | EXISTS | tests/chat/test_router.py has 2 passing tests |

**Key insight:** The UI shell is already built (Phase 2). Phase 4 is almost entirely backend prompt + one frontend section addition.

---

## Requirements

| Req | Description | Done? |
|-----|-------------|-------|
| SYN-01 | Narrative synthesis across multiple articles, not excerpts | DONE |
| SYN-02 | `[FROM YOUR SOURCES]` and `[ANALYSIS]` sections with distinct visual styling | DONE |
| SYN-03 | Clickable source citations per response | DONE |
| SYN-04 | Contradictions surfaced explicitly when sources disagree | DONE (frontend renders [CONTRADICTIONS] in rose; backend prompts for it) |

---

## Tasks

### Task 0 — Baseline check (read-only)
**Status:** SKIPPED (current state was verified during sprint planning)
**Why:** Before changing the prompt, confirm what current output looks like.

```bash
# Start backend if not running:
cd /Users/gauravarora/Documents/Articleresearchthoughts
backend/.venv/bin/uvicorn api.index:app --host 0.0.0.0 --port 8000 \
  --app-dir /Users/gauravarora/Documents/Articleresearchthoughts --log-level info &

# Test a synthesis query:
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "test-conv", "message": "What do my saved articles say about AI safety?"}' \
  | python3 -m json.tool | head -40
```

Expected current output: likely returns excerpts or a list, may or may not include section markers.

---

### Task 1 — Upgrade synthesis system prompt + increase top_k
**Status:** DONE — 2 tests passed
**File:** `backend/second_brain/chat/router.py`

**Replace the SYSTEM_PROMPT constant** (lines 23–30) with:

```python
SYSTEM_PROMPT = (
    "You are a personal knowledge assistant. The user asks questions about articles, "
    "essays, and ideas saved to their Second Brain.\n\n"
    "ALWAYS structure your response with these exact markers:\n\n"
    "[FROM YOUR SOURCES]\n"
    "Write a narrative synthesis — NOT bullet points or raw excerpts — of what the "
    "user's saved articles say about this topic. Weave insights from multiple sources "
    "together into flowing prose. Cite article titles inline using bold: **Title**. "
    "If fewer than 2 sources are relevant, say so honestly.\n\n"
    "[ANALYSIS]\n"
    "Your own synthesis: what patterns emerge across sources, what tensions exist, "
    "what the user's reading suggests about their thinking on this topic.\n\n"
    "ONLY include this section if two or more sources genuinely contradict each other:\n\n"
    "[CONTRADICTIONS]\n"
    "Surface the specific disagreement: '**Source A** argues X, while **Source B** argues Y.'\n\n"
    "Rules: always include [FROM YOUR SOURCES] and [ANALYSIS]. Only include "
    "[CONTRADICTIONS] when a real contradiction exists — do not manufacture one. "
    "Never fabricate sources. Be specific and cite titles."
)
```

**Also change `top_k` from 5 to 10** on this line in the `chat_endpoint` function:
```python
# Before:
sources: list[SearchResult] = hybrid_search(body.message, top_k=5)

# After:
sources: list[SearchResult] = hybrid_search(body.message, top_k=10)
```

**Verify:**
```bash
cd backend && uv run pytest tests/chat/test_router.py -q
# Expected: 2 passed
```

---

### Task 2 — Add [CONTRADICTIONS] section to MessageBubble
**Status:** DONE — tsc passes with no errors
**File:** `frontend/src/components/MessageBubble.tsx`

The `parseAssistantSections` function currently handles `[FROM YOUR SOURCES]` and `[ANALYSIS]`. Add `[CONTRADICTIONS]` support.

**Step A — Add the marker constant and parsing** in `parseAssistantSections`:

Replace the existing function body with one that handles three markers in order.
The markers in natural response order are: `[FROM YOUR SOURCES]` → `[ANALYSIS]` → `[CONTRADICTIONS]`.
But `[CONTRADICTIONS]` could appear in any order after `[FROM YOUR SOURCES]`, so parse all three by index.

```typescript
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
```

**Step B — Add the CONTRADICTIONS render block** in the `sections.map(...)` inside `MessageBubble`, after the ANALYSIS block:

```tsx
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
```

**Verify (import check):**
```bash
cd frontend && npx tsc --noEmit
# Expected: no errors
```

---

### Task 3 — Human verify end-to-end
**Status:** DONE — verified 2026-04-01
**Depends on:** Tasks 1 and 2

1. **Restart the backend** to pick up the new prompt:
   ```bash
   # Kill existing process and restart
   pkill -f "uvicorn api.index:app" || true
   cd /Users/gauravarora/Documents/Articleresearchthoughts
   backend/.venv/bin/uvicorn api.index:app --host 0.0.0.0 --port 8000 \
     --app-dir /Users/gauravarora/Documents/Articleresearchthoughts --log-level info &
   ```

2. **Open the chat UI** at `http://localhost:3000` and ask a synthesis question:
   - "What do my saved articles say about AI safety?"
   - "What have I read about the future of work?"
   - "What do my sources say about OpenAI vs Google?"

3. **Check the response:**
   - Does it include `[FROM YOUR SOURCES]` rendered in blue?
   - Does it include `[ANALYSIS]` rendered in amber?
   - Does it cite article titles in **bold**?
   - If sources contradict: does `[CONTRADICTIONS]` appear in rose/red?
   - Are 10 citation cards shown below the message?

4. **Run the full test suite:**
   ```bash
   cd backend && uv run pytest tests/ -q
   # Expected: 28 passed
   ```

**Resume signal:** Type "verified" or "issues: [description]"

---

## What Remains After Sprint 4

| Phase | What | Key deliverable |
|-------|------|----------------|
| Phase 5 | Proactive Insights + Digests | Weekly digest, unseen insight badge in UI, system notices patterns without being asked |

---

## Progress Log

| Date | What happened |
|------|--------------|
| 2026-04-01 | Sprint 4 file created. Current state assessed: frontend shell done (Phase 2), backend prompt weak, top_k=5, no contradiction detection. |
| 2026-04-01 | Sprint 4 executed and verified. Fixed: synthesis prompt, top_k→30 with source dedup, two-stage SQL (ivfflat index), [CONTRADICTIONS] section in UI. Tested against Obsidian query — [FROM YOUR SOURCES] + [ANALYSIS] rendered correctly, bold title citations working. |
| 2026-04-02 | Post-sprint fixes: reverted ivfflat two-stage SQL back to full-scan (ANN with probes=1 was missing relevant chunks); fixed readwise.py to store source_url not reader URL (694 records backfilled, 350 tweets now have correct x.com URLs); fixed backfill_missing_chunks pagination bug (was capped at 1000 rows, caused 27K duplicate chunks — deduped and cleaned up). |

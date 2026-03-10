---
phase: 02-chat-ui-memory
plan: 02
subsystem: ui
tags: [nextjs, react, typescript, tailwind, shadcn, react-markdown, sse, streaming]

# Dependency graph
requires:
  - phase: 02-chat-ui-memory
    plan: 01
    provides: "FastAPI chat endpoints: POST /api/chat SSE, POST/GET /api/conversations, GET /api/conversations/{id}/messages — consumed by api.ts fetch wrappers"

provides:
  - "Next.js 16 App Router frontend scaffold at frontend/ with TypeScript, Tailwind, shadcn/ui"
  - "frontend/src/lib/types.ts: Message, Conversation, Source, ChatEvent TypeScript interfaces"
  - "frontend/src/lib/api.ts: sendMessage() SSE streaming client, fetchConversations(), fetchMessages(), createConversation()"
  - "frontend/src/components/CitationCard.tsx: expandable source card with title/author, URL opens on click (UI-02)"
  - "frontend/src/components/MessageBubble.tsx: markdown rendering with [FROM YOUR SOURCES] blue styling and [ANALYSIS] amber styling (UI-03)"
  - "frontend/src/components/ConvSidebar.tsx: shadcn Sidebar with past conversations list; active conversation highlighted (UI-04)"
  - "frontend/src/components/ChatPanel.tsx: streaming chat area with SSE token accumulation and error handling"
  - "/chat route: auto-creates conversation on mount; /chat/[id] route: loads message history"

affects: [02-03, 02-04, 02-05, vercel-deploy]

# Tech tracking
tech-stack:
  added: [next@16.1.6, react, react-dom, typescript, tailwindcss, shadcn-ui, react-markdown, remark-gfm, clsx, tailwind-merge, class-variance-authority, concurrently]
  patterns: ["SSE ReadableStream reader with buffer split on double-newline", "Optimistic UI: user message added instantly; assistant placeholder accumulates tokens", "Memoized react-markdown to prevent re-render thrash during streaming", "Client components for interactivity; Server component shell for pages with async params"]

key-files:
  created:
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/components.json
    - frontend/tsconfig.json
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
    - frontend/src/app/globals.css
    - frontend/src/lib/types.ts
    - frontend/src/lib/api.ts
    - frontend/src/lib/utils.ts
    - frontend/src/components/ui/sidebar.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/scroll-area.tsx
    - frontend/src/components/ui/textarea.tsx
    - frontend/src/components/CitationCard.tsx
    - frontend/src/components/MessageBubble.tsx
    - frontend/src/components/ConvSidebar.tsx
    - frontend/src/components/ChatPanel.tsx
    - frontend/src/app/chat/page.tsx
    - frontend/src/app/chat/NewChatClient.tsx
    - frontend/src/app/chat/[id]/page.tsx
    - frontend/src/app/chat/[id]/ExistingChatClient.tsx
  modified: []

key-decisions:
  - "Async params pattern for /chat/[id]/page.tsx — Next.js 15+ requires params as Promise<{id}>, not {id} directly; using async server component that awaits params before passing to client component"
  - "lib/utils.ts created manually — shadcn init is interactive; wrote components.json and ran `shadcn add` non-interactively instead, then created utils.ts with clsx + tailwind-merge manually"
  - "MemoizedMarkdown wraps react-markdown in React.memo to prevent full re-render on every streaming token"
  - "NewChatClient and ExistingChatClient are separate client components so chat pages can have a server component shell"

patterns-established:
  - "Client/Server split: page.tsx is a server component shell; *Client.tsx files handle state and effects"
  - "SSE buffer pattern: split on double-newline, keep last incomplete chunk, parse each data: line"
  - "Section marker parsing: detect [FROM YOUR SOURCES] and [ANALYSIS] at indexOf, slice content into labeled sections for distinct styling"

requirements-completed: [UI-02, UI-03, UI-04]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 2 Plan 02: Chat UI Summary

**Next.js 16 streaming chat interface with expandable source citation cards, [FROM YOUR SOURCES]/[ANALYSIS] visual section styling, and a shadcn conversation sidebar**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T20:06:09Z
- **Completed:** 2026-03-10T20:10:00Z
- **Tasks:** 2
- **Files modified:** 23

## Accomplishments

- Delivered a complete Next.js 16 frontend scaffold with TypeScript, Tailwind CSS, shadcn/ui components, and dev proxy routing /api/* to FastAPI on port 8000
- Built streaming chat UI that reads SSE tokens in real time and accumulates them into an assistant message placeholder; memoized markdown rendering prevents re-render thrash
- Implemented UI-02 (expandable citation cards), UI-03 (blue/amber section styling for FROM YOUR SOURCES / ANALYSIS), UI-04 (conversation sidebar with past chats)

## Task Commits

Each task was committed atomically:

1. **Task 1: Next.js scaffold + shared types and API client** - `b57d329` (feat)
2. **Task 2: Chat components — MessageBubble, CitationCard, ConvSidebar, ChatPanel, and chat pages** - `9748e73` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `frontend/next.config.ts` - Dev proxy: /api/* → localhost:8000
- `frontend/components.json` - shadcn/ui configuration
- `frontend/src/lib/types.ts` - Message, Conversation, Source, ChatEvent interfaces
- `frontend/src/lib/api.ts` - sendMessage() SSE client + fetch wrappers for all endpoints
- `frontend/src/lib/utils.ts` - cn() helper (clsx + tailwind-merge)
- `frontend/src/app/layout.tsx` - Root layout with SidebarProvider wrapper
- `frontend/src/app/page.tsx` - Root redirect to /chat
- `frontend/src/components/CitationCard.tsx` - Expandable source card (UI-02)
- `frontend/src/components/MessageBubble.tsx` - Markdown rendering + section styling (UI-02, UI-03)
- `frontend/src/components/ConvSidebar.tsx` - Past conversations sidebar (UI-04)
- `frontend/src/components/ChatPanel.tsx` - Streaming chat input + message list
- `frontend/src/app/chat/page.tsx` - New conversation page (server shell)
- `frontend/src/app/chat/NewChatClient.tsx` - Creates conversation on mount
- `frontend/src/app/chat/[id]/page.tsx` - Existing conversation page (async params)
- `frontend/src/app/chat/[id]/ExistingChatClient.tsx` - Loads message history

## Decisions Made

- Used async params pattern for `/chat/[id]/page.tsx` — Next.js 15+ changed params to a Promise; the page is an async server component that awaits params before rendering
- Created `components.json` manually and ran `shadcn add` non-interactively (shadcn init is interactive and cannot be automated); created `lib/utils.ts` with clsx + tailwind-merge manually
- Wrapped react-markdown in `React.memo` as `MemoizedMarkdown` to prevent re-render thrash on every token during streaming
- Split pages into server component shell + `*Client.tsx` client component to preserve server-side benefits while keeping interactivity

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Next.js version is 16 (not 15) — async params required**
- **Found during:** Task 2 (writing /chat/[id]/page.tsx)
- **Issue:** create-next-app installed Next.js 16.1.6; in Next.js 15+, dynamic route params are a Promise, not a plain object — using `params: { id: string }` causes a type error
- **Fix:** Changed page Props to `params: Promise<{ id: string }>` and made the page component async with `const { id } = await params`
- **Files modified:** frontend/src/app/chat/[id]/page.tsx
- **Verification:** TypeScript compiles with no errors; `npm run build` succeeds
- **Committed in:** 9748e73 (Task 2 commit)

**2. [Rule 3 - Blocking] shadcn init is interactive — cannot be automated**
- **Found during:** Task 1 (scaffolding)
- **Issue:** `npx shadcn@latest init --yes` still presents interactive component library and preset selection prompts; cannot be driven via stdin
- **Fix:** Wrote `components.json` manually with correct shadcn v4 schema, then ran `npx shadcn@latest add` (non-interactive); created `lib/utils.ts` manually with clsx + tailwind-merge
- **Files modified:** frontend/components.json, frontend/src/lib/utils.ts
- **Verification:** All shadcn component imports resolve; TypeScript passes
- **Committed in:** b57d329 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking)
**Impact on plan:** Both fixes required for correct compilation and automation. No scope creep.

## Issues Encountered

- shadcn CLI v4 is interactive even with `--yes`; worked around by manual components.json + direct `shadcn add` command
- Next.js version installed (16.1.6) is newer than plan expected (15); async params pattern applied

## User Setup Required

None — no external service configuration required. The frontend can be started with `npm run dev` from the `frontend/` directory; it will proxy API calls to FastAPI on port 8000.

## Next Phase Readiness

- Frontend scaffold complete and builds successfully
- Chat UI delivers streaming responses, citation cards, section styling, conversation sidebar
- UI-02, UI-03, UI-04 requirements satisfied
- Plans 02-03 (ingestion panel) and 02-04 (Vercel deploy) can extend this scaffold

---
*Phase: 02-chat-ui-memory*
*Completed: 2026-03-10*

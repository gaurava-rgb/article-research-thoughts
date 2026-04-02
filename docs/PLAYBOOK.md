# Playbook

## Purpose

This file explains how to work on this repo with Cursor without falling back into context rot or black-box orchestration.

## Default Session Startup

Read:

1. `CURSORPLAN.md`
2. `docs/PROJECT.md`
3. `docs/NOW.md`
4. `docs/DECISIONS.md`

Then do:

- summarize the current task
- list likely files
- propose the smallest useful plan
- stop and wait if the task is still too large

## Default Implementation Prompt

Use this when starting normal work:

```md
Read `CURSORPLAN.md`, `docs/PROJECT.md`, `docs/NOW.md`, and `docs/DECISIONS.md`.
If needed, also read `docs/ARCHITECTURE.md`.

Summarize:
- the current goal
- what is in scope
- likely files
- the smallest implementation plan

Do only the work required by `docs/NOW.md`.
Do not continue into unrelated cleanup.
Before declaring the task complete, run the mandatory closeout in `docs/CLOSEOUT.md`.
Update all required markdown files before ending the task.
```

## Planning Prompt

Use this when the next task is still too ambiguous:

```md
Read `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/NOW.md`.
Do not code yet.

Give:
- the smallest shippable task breakdown
- risks and tradeoffs
- the recommended first step

Keep the plan concrete and short.
```

## Debug Prompt

Use this when something is broken:

```md
Read `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/NOW.md`, and only the relevant code paths.

Do not broadly refactor.
First:
- explain likely root causes
- identify the smallest fix
- identify how to verify it

Then implement only that fix.
Before declaring the task complete, run the mandatory closeout in `docs/CLOSEOUT.md`.
```

## Review Prompt

Use this when asking for a review:

```md
Review the current implementation for bugs, regressions, missing edge cases, and UX problems.
Prioritize findings over summaries.
Keep the review tied to the current task in `docs/NOW.md`.
```

## UI Prompt

Use this for frontend work:

```md
Read `docs/PROJECT.md`, `docs/NOW.md`, and the relevant frontend files.

Evaluate the task as a product experience, not just a component checklist.
Focus on:
- empty states
- loading states
- interaction clarity
- honesty of copy
- whether it feels intentional in use

Do not mark placeholder behavior as complete UX.
```

## Task Sizing Rules

A task is small enough when:

- one clear goal fits in `docs/NOW.md`
- likely files are limited
- success can be verified without needing a giant follow-up task
- the task can reasonably be reviewed in one sitting

Split the task if:

- it spans backend, frontend, schema, and deployment all at once
- you need more than one architectural decision before coding
- the agent would have to "keep going" through multiple waves to feel done

## When To Use More Structure

Use extra planning for:

- schema changes
- API redesign
- Phase 4 synthesis architecture
- Phase 5 background workflow design

Do not over-structure:

- UI polish
- loading-state fixes
- bug reproduction and repair
- small feature completion

## Update Rules

Update:

- `docs/NOW.md` when the active task changes or is completed
- `docs/PROGRESS.md` after every completed task or meaningful investigation
- `docs/DECISIONS.md` when a real decision is made
- `docs/ARCHITECTURE.md` when architecture changes
- `docs/PROJECT.md` only when product truth changes
- `docs/TODO.md` when ordering or status changes

These updates are not optional cleanup.

A task is not done until the required docs are updated.

## Mandatory Closeout

At the end of every successful task:

1. update `docs/PROGRESS.md`
2. update `docs/NOW.md`
3. update `docs/DECISIONS.md` if a real decision was made
4. update `docs/ARCHITECTURE.md` if architecture changed
5. update `docs/PROJECT.md` if product truth changed
6. update `docs/TODO.md` if sequencing or status changed
7. explicitly report which docs were updated before ending the task

Use `docs/CLOSEOUT.md` as the exact checklist.

## Stop Conditions

Stop and ask before continuing when:

- a task is becoming broader than `docs/NOW.md`
- the correct implementation path is unclear
- UI decisions need human taste judgment
- the agent notices surprising unrelated changes

## Anti-Patterns

Avoid:

- giant phase prompts for everyday work
- continuing into the next milestone automatically
- treating component presence as proof of product quality
- loading every planning file into every session
- turning debugging into multi-agent orchestration

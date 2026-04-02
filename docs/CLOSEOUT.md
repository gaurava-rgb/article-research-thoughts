# Closeout

This file is the mandatory end-of-task checklist.

A task is not considered complete until this checklist has been followed.

## Rule

If code changed, docs must be updated before the task is declared done.

If no code changed but understanding changed in a meaningful way, docs still need to be updated to reflect that new reality.

## Always Update

### 1. `docs/PROGRESS.md`

Record:

- what was completed
- what was verified
- any remaining issues or caveats

### 2. `docs/NOW.md`

Update it so it reflects one of these states:

- the task is complete and the next task is chosen
- the task is complete and awaiting the next task choice
- the task is blocked
- the task has been reframed

It should never keep describing a stale task after a task is done.

## Update When Needed

### 3. `docs/DECISIONS.md`

Update when:

- a real technical decision was made
- a workflow decision changed
- an implementation choice now constrains future work

### 4. `docs/ARCHITECTURE.md`

Update when:

- system design changed
- a new durable component or workflow was introduced
- a previous architectural assumption became false

### 5. `docs/PROJECT.md`

Update when:

- product truth changed
- scope or end-state capabilities changed
- a future capability was added, removed, or reframed

### 6. `docs/TODO.md`

Update when:

- task order changed
- a todo item moved to in progress or done
- a new important item was discovered

## Final Response Requirement

Before ending a task, explicitly report:

- which docs were updated
- which docs were intentionally not updated and why

## Failure Condition

If the implementation is finished but the docs are stale, the task is still incomplete.

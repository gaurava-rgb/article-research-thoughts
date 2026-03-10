---
phase: 2
slug: chat-ui-memory
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest / playwright (frontend) |
| **Config file** | `pytest.ini` or `pyproject.toml` (backend), `vitest.config.ts` (frontend) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | UI-01 | e2e | `npx playwright test` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | UI-02 | e2e | `npx playwright test` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | UI-03 | e2e | `npx playwright test` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | CHAT-01 | integration | `pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | CHAT-02 | integration | `pytest tests/test_chat.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | CHAT-03 | integration | `pytest tests/test_memory.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | CHAT-04 | integration | `pytest tests/test_memory.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-03 | 02 | 2 | UI-04 | e2e | `npx playwright test` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 3 | UI-05 | e2e | `npx playwright test` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 3 | UI-07 | e2e | `npx playwright test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_chat.py` — stubs for CHAT-01, CHAT-02, CHAT-03, CHAT-04
- [ ] `tests/test_memory.py` — stubs for cross-session memory (CHAT-04)
- [ ] `tests/conftest.py` — shared fixtures (DB connection, test client)
- [ ] `frontend/e2e/chat.spec.ts` — Playwright stubs for UI-01 through UI-07
- [ ] `playwright.config.ts` — Playwright config pointing at local dev server

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Vercel deployment accessible via URL | UI-05 | Requires live deploy environment | Deploy to Vercel, visit URL, confirm chat loads |
| Readwise sync trigger from UI | UI-07 | Requires Readwise API credentials in production | Click sync button in ingestion panel, verify articles appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

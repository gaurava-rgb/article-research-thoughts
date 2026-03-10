---
phase: 3
slug: clustering-topic-evolution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already in pyproject.toml dev deps) |
| **Config file** | `backend/pyproject.toml` (no pytest.ini; pytest picks up `tests/`) |
| **Quick run command** | `cd backend && python -m pytest tests/clustering/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/clustering/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | STR-01 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_assign_to_existing_topic -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 0 | STR-01 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_create_new_topic -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 0 | STR-01 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_source_topics_row_created -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 0 | STR-02 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_summary_regenerated -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 0 | STR-02 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_summary_deduplication -x` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 0 | STR-03 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_temporal_filter -x` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 0 | STR-03 | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_temporal_null_fallback -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/clustering/__init__.py` — new test package
- [ ] `backend/tests/clustering/test_clustering.py` — stubs for all STR-xx tests above with mocked DB + LLM

*Uses `unittest.mock.patch` and `MagicMock` consistent with existing test patterns in `tests/chat/`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Topics assigned correctly after a real Readwise sync | STR-01 | Requires live Readwise API + real embeddings | Run `python -m second_brain.cli sync`, then query `SELECT * FROM source_topics` to verify new articles have topic assignments |
| Topic summary reads naturally for a real topic | STR-02 | Subjective quality check | After sync, query `SELECT name, summary FROM topics` and read 3-5 summaries for coherence |
| Temporal query returns grounded answer | STR-03 | Requires live chat + real publication dates | Ask "What changed about X between 2024 and 2025?" and verify answer cites articles with dates in that range |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

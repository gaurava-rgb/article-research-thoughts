# Phase 3: Clustering + Topic Evolution - Research

**Researched:** 2026-03-10
**Domain:** Embedding-based topic clustering, incremental topic assignment, LLM-driven topic summarization, temporal querying
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STR-01 | New articles are automatically assigned to topics (clusters) on ingestion — no manual tagging required | Covered by embedding similarity scan against existing topic centroids + LLM fallback to create new topic |
| STR-02 | Topic summaries are automatically rewritten when new articles join a topic | Covered by LLM regeneration call on `source_topics` join, triggered post-assignment |
| STR-03 | System tracks publication dates to enable temporal reasoning across topics | `published_at` already stored in `sources`; covered by SQL filtered queries and temporal prompt patterns |
</phase_requirements>

---

## Summary

This phase adds automatic topic clustering to the ingestion pipeline. When a new article is synced, its stored `sources.source_embedding` is compared against existing topic centroids. If it is sufficiently similar to an existing topic (cosine similarity >= threshold), it is assigned there. If no existing topic is close enough, the LLM names a new topic and the article seeds it. After assignment, the topic summary is regenerated from the titles of all sources in that topic.

The schema already has most of what Phase 3 needs: `topics` (id, name, summary), `source_topics` (join), `published_at` on every source row, and durable whole-source vectors on `sources.source_embedding`. Phase 3 should reuse `sources.source_embedding` as the source-level vector of record rather than inventing a second source embedding column or reverting to a chunk-average flow. The remaining schema addition is a `centroid_embedding` column on `topics`, plus an optional `match_topic` SQL helper.

The recommended approach is **LLM-guided centroid matching** rather than a library like BERTopic or HDBSCAN. This is appropriate because: (a) the corpus is personal-scale (hundreds to low thousands of articles, not millions), (b) HDBSCAN does not support incremental document addition without full re-clustering, (c) the project already has an LLM provider abstraction ready to use, and (d) simplicity is a declared constraint ("learning coder").

**Primary recommendation:** At sync time, for each new article reuse the stored `sources.source_embedding`, compare against stored topic centroids, assign to the best-matching topic if similarity >= 0.65, otherwise create a new topic via LLM naming. Older rows that still lack `source_embedding` should be handled by an explicit backfill or repair path, not by silently drifting back to stale plan assumptions. After any assignment, regenerate the topic summary via LLM. Temporal queries are answered by filtering on `sources.published_at` in existing or new SQL functions.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 1.x / 2.x (already available via supabase deps) | Cosine similarity between source embedding and topic centroid vectors | Standard Python numerics; no extra dep needed |
| openai (already in pyproject.toml) | current | LLM calls for topic naming + summary regeneration | Already wired via OpenRouterLLMProvider |
| supabase-py (already in pyproject.toml) | current | Storing/querying topic centroids, source_topics rows | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | any | Vector math for cosine similarity + centroid averaging | Required for in-memory centroid comparison |
| tiktoken (already in pyproject.toml) | any | No new use; already used for chunking | N/A |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LLM-guided centroid matching | HDBSCAN + BERTopic | HDBSCAN cannot incrementally add a single document to an existing cluster — requires full re-cluster each sync; too complex for this scale |
| LLM-guided centroid matching | k-means | k-means requires specifying k in advance; corpus will grow unpredictably |
| LLM-guided centroid matching | BERTopic online (.partial_fit) | Requires IncrementalPCA + MiniBatchKMeans swap; heavy dependency for personal-scale corpus; LLM approach gives human-readable topic names without extra labeling step |
| numpy cosine similarity | pgvector `<=>` operator | Could query `SELECT ... ORDER BY centroid_embedding <=> $1 LIMIT 1` in SQL; valid alternative but requires topics table to have a centroid_embedding column either way; SQL approach is fine too |

**Installation (numpy only new dep):**
```bash
cd backend && uv add numpy
```
numpy is likely already a transitive dependency of supabase/httpx chain; verify with `uv pip show numpy` before adding.

---

## Architecture Patterns

### Recommended Project Structure
```
backend/second_brain/
├── ingestion/
│   ├── readwise.py          # existing — now also writes source_embedding during ingestion
│   ├── chunker.py           # existing — no changes
│   └── clustering.py        # NEW — topic assignment logic
├── retrieval/
│   └── search.py            # existing — may add topic-filtered search helper
├── providers/
│   └── llm.py               # existing — reuse for topic naming + summary
├── cli.py                   # extend sync command to call assign_topics_to_source()
└── chat/
    └── router.py            # may expose GET /api/topics endpoint for Phase 4 use
```

### Pattern 1: Reuse Stored Source-Level Embeddings
**What:** Read the article-level vector already stored on `sources.source_embedding`. This is the current ingestion reality and should be the Phase 3 source of truth.
**When to use:** At topic-assignment time, after fetching the source row.
**Example:**
```python
def get_source_embedding(source_id: str, db) -> list[float] | None:
    """Return the stored whole-source embedding, if present."""
    rows = (
        db.table("sources")
        .select("source_embedding")
        .eq("id", source_id)
        .execute()
    ).data
    if not rows:
        return None
    return rows[0].get("source_embedding")
```

### Pattern 2: Cosine Similarity Against Topic Centroids
**What:** Load all existing topic centroids from the `topics` table, compute cosine similarity to the new source embedding, pick the highest-scoring topic if it clears the threshold.
**When to use:** Each time a new article is stored, before deciding to assign or create a topic.
**Example:**
```python
# Source: supabase.com/docs/guides/ai/semantic-search (match_threshold pattern)
SIMILARITY_THRESHOLD = 0.65  # tunable; 0.65 is a reasonable starting point

def find_best_topic(
    source_embedding: list[float],
    db,
) -> tuple[str | None, float]:
    """
    Return (topic_id, similarity) for the best-matching existing topic,
    or (None, 0.0) if no topic clears the threshold.

    Uses cosine similarity: 1 - cosine_distance.
    pgvector's <=> is cosine DISTANCE (0=identical, 2=opposite).
    So similarity = 1 - (embedding <=> query) for normalized vectors.
    """
    rows = db.table("topics").select("id, centroid_embedding").execute().data
    if not rows:
        return None, 0.0

    best_id, best_score = None, 0.0
    source_vec = np.array(source_embedding, dtype=np.float32)

    for row in rows:
        if row["centroid_embedding"] is None:
            continue
        topic_vec = np.array(row["centroid_embedding"], dtype=np.float32)
        # Both vectors are normalized — dot product equals cosine similarity
        score = float(np.dot(source_vec, topic_vec))
        if score > best_score:
            best_score = score
            best_id = row["id"]

    if best_score >= SIMILARITY_THRESHOLD:
        return best_id, best_score
    return None, best_score
```

### Pattern 3: LLM-Driven Topic Naming
**What:** When no existing topic matches, ask the LLM to name a new topic from the article title + first chunk excerpt.
**When to use:** When `find_best_topic` returns `(None, _)`.
**Example:**
```python
# Source: project's existing OpenRouterLLMProvider.complete() pattern
def name_new_topic(title: str, excerpt: str, llm) -> str:
    """
    Ask the LLM for a short topic name (3-6 words) for a new cluster.
    The name must be specific enough to distinguish it from likely siblings.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a knowledge organizer. Given an article title and excerpt, "
                "produce a SHORT topic label (3–6 words) that captures the core theme. "
                "Return only the label — no explanation, no punctuation at the end."
            ),
        },
        {
            "role": "user",
            "content": f"Title: {title}\n\nExcerpt: {excerpt[:400]}",
        },
    ]
    return llm.complete(messages).strip()
```

### Pattern 4: Topic Summary Regeneration (STR-02)
**What:** After assigning a source to a topic, regenerate the topic summary by listing all source titles in that topic and asking the LLM to write a 2-3 sentence summary.
**When to use:** Every time a new source is assigned to a topic.
**Example:**
```python
# Source: project's existing LLM provider pattern
def regenerate_topic_summary(topic_id: str, db, llm) -> str:
    """Rewrite the topic summary to reflect all current member articles."""
    rows = (
        db.table("source_topics")
        .select("sources(title, published_at)")
        .eq("topic_id", topic_id)
        .execute()
    ).data
    titles = [r["sources"]["title"] for r in rows if r.get("sources")]
    if not titles:
        return ""
    titles_list = "\n".join(f"- {t}" for t in titles[:30])  # cap at 30 to limit tokens
    messages = [
        {
            "role": "system",
            "content": (
                "You are a knowledge organizer. Given a list of article titles that "
                "belong to the same topic cluster, write a 2-3 sentence summary of "
                "what this topic covers. Be specific and informative."
            ),
        },
        {"role": "user", "content": f"Articles in this topic:\n{titles_list}"},
    ]
    return llm.complete(messages).strip()
```

### Pattern 5: Centroid Update After Assignment
**What:** After a source joins a topic, recompute the topic centroid as the mean of all member source embeddings. Store back to `topics.centroid_embedding`.
**When to use:** Every time the `source_topics` table is updated.
**Example:**
```python
# Standard incremental centroid update; sources: numpy docs + pgvector avg() docs
def update_topic_centroid(topic_id: str, db) -> None:
    """
    Recompute and persist the topic centroid embedding.
    Uses AVG of all source embeddings that belong to the topic.
    source_embeddings are pre-computed and stored on `sources.source_embedding`.
    """
    rows = (
        db.table("source_topics")
        .select("sources(source_embedding)")
        .eq("topic_id", topic_id)
        .execute()
    ).data
    vectors = [
        np.array(r["sources"]["source_embedding"], dtype=np.float32)
        for r in rows
        if r.get("sources") and r["sources"].get("source_embedding")
    ]
    if not vectors:
        return
    centroid = np.mean(vectors, axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm
    db.table("topics").update({"centroid_embedding": centroid.tolist()}).eq("id", topic_id).execute()
```

### Pattern 6: Temporal Query Support (STR-03)
**What:** The `published_at` column on `sources` already exists and is indexed. Temporal queries are answered by filtering `hybrid_search()` with `after=` / `before=` parameters, or by adding a topic-scoped temporal query. No new tables are needed.
**When to use:** Chat queries that mention time periods ("Q3 2024", "last year", etc.) — handled in Phase 4's synthesis layer. Phase 3 must ensure `published_at` is populated and non-null for the majority of sources, and provide a helper to retrieve sources-by-topic filtered by date range.
**Example:**
```python
# Verified: sources.published_at already stored in schema.sql; hybrid_search already accepts date_after/date_before
def get_topic_sources_by_date(
    topic_id: str,
    after: str | None,
    before: str | None,
    db,
) -> list[dict]:
    """Return sources in a topic, filtered by publication date range."""
    q = (
        db.table("source_topics")
        .select("sources(id, title, author, url, published_at)")
        .eq("topic_id", topic_id)
    )
    result = q.execute()
    rows = [r["sources"] for r in result.data if r.get("sources")]
    if after:
        rows = [r for r in rows if r.get("published_at") and r["published_at"] >= after]
    if before:
        rows = [r for r in rows if r.get("published_at") and r["published_at"] <= before]
    return rows
```

### Anti-Patterns to Avoid

- **Running full HDBSCAN re-cluster on every sync:** Produces unstable topic IDs (topics shift meaning) and discards all prior `source_topics` assignments. Never do this for an incremental system.
- **Inventing a new `sources.embedding` column or recomputing chunk averages because of stale plan text:** The current ingestion path already persists whole-source vectors on `sources.source_embedding`. Reuse that column, and treat missing historical values as a repair/backfill concern.
- **Calling the LLM to name a topic for every article:** Only call the LLM when no existing topic clears the threshold. Existing-topic assignment is purely vector math and costs zero LLM tokens.
- **Regenerating all topic summaries after every sync:** Only regenerate topics that received new members in the current sync batch.
- **Using pgvector `<=>` cosine DISTANCE as cosine SIMILARITY without correction:** `<=>` returns distance (0 = identical). Similarity = 1 - distance. The codebase already has this pattern in `hybrid_search` (`1 - (c.embedding <=> query_embedding)`).

---

## Schema Changes Required

The existing schema already has `sources.source_embedding` for whole-source vectors. Phase 3 should validate and reuse that column, not add a second source embedding field.

### Addition 1: `topics.centroid_embedding`
```sql
-- Add to schema.sql (Phase 3 additions section)
ALTER TABLE topics ADD COLUMN IF NOT EXISTS centroid_embedding vector(1536);
```
Stores the running centroid of all member source embeddings. Updated after each assignment.

### Addition 2: SQL helper function `match_topic`
```sql
-- Optional but clean: find best-matching topic for a given embedding
CREATE OR REPLACE FUNCTION match_topic(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.65,
  match_count int DEFAULT 1
)
RETURNS TABLE (topic_id uuid, topic_name text, similarity float)
LANGUAGE sql STABLE AS $$
  SELECT
    id AS topic_id,
    name AS topic_name,
    1 - (centroid_embedding <=> query_embedding) AS similarity
  FROM topics
  WHERE centroid_embedding IS NOT NULL
    AND 1 - (centroid_embedding <=> query_embedding) >= match_threshold
  ORDER BY centroid_embedding <=> query_embedding
  LIMIT match_count;
$$;
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity | Custom trig formula | numpy dot product on normalized vectors | Already normalized; dot product is cosine similarity for unit vectors |
| Topic name generation | Rule-based keyword extraction | Existing LLM provider via `llm.complete()` | LLM produces human-readable names; keyword extraction misses context |
| Incremental clustering | HDBSCAN re-run pipeline | Centroid threshold approach in `clustering.py` | HDBSCAN cannot add a single document; centroid approach is O(N_topics) per article |
| Summary regeneration | Custom summarizer | Existing LLM provider via `llm.complete()` | Summarization is a solved problem for this scale |
| Date-range filtering | Custom date parser in Python | Existing `after`/`before` params in `hybrid_search()` | Already implemented and tested |

**Key insight:** At personal-knowledge-base scale (< 5000 articles), vector centroid matching with a cosine threshold is not only simpler than HDBSCAN or k-means but also produces more stable incremental results because topics are never re-numbered or merged without an explicit action.

---

## Common Pitfalls

### Pitfall 1: HDBSCAN Re-cluster on Every Sync
**What goes wrong:** Each sync re-assigns all articles to new cluster numbers, breaking `source_topics` foreign key relationships and making topic IDs unstable.
**Why it happens:** Developers apply batch clustering to the whole corpus without considering that prior assignments must remain valid.
**How to avoid:** Use the centroid-threshold approach. Only create/assign; never delete or re-index existing topic assignments.
**Warning signs:** Topic IDs in `source_topics` stop matching `topics` table rows after a sync.

### Pitfall 2: Centroid Drift Without Normalization
**What goes wrong:** After many articles join a topic, the centroid drifts toward the majority of articles, making it biased. New articles that should join never clear the threshold.
**Why it happens:** Averaging non-normalized vectors inflates magnitude for dominant directions.
**How to avoid:** Normalize every source embedding and every centroid to unit length before storing. Then dot product = cosine similarity.
**Warning signs:** Topics accumulate hundreds of articles; new related articles are incorrectly assigned to a new topic.

### Pitfall 3: pgvector Cosine Distance vs. Similarity Confusion
**What goes wrong:** The `<=>` operator returns cosine DISTANCE (0 = identical, 2 = opposite). Comparing it directly to a 0.65 similarity threshold yields wrong results.
**Why it happens:** Documentation mixes "distance" and "similarity" terminology.
**How to avoid:** Always use `similarity = 1 - (embedding <=> query)` (as done in `hybrid_search`). Match threshold is `distance < 1 - threshold`.
**Warning signs:** All articles assigned to the same topic, or no articles ever exceeding the threshold.

### Pitfall 4: LLM Called for Every Article Assignment
**What goes wrong:** Each sync calls the LLM once per new article even for articles that match an existing topic, burning tokens unnecessarily.
**Why it happens:** LLM naming and threshold check are not separated.
**How to avoid:** Check centroid similarity first (pure vector math, free). Only call LLM if no topic is found.
**Warning signs:** Sync takes 10+ minutes; OpenRouter bill spikes on sync days.

### Pitfall 5: sources.published_at is NULL for Many Articles
**What goes wrong:** Temporal queries return empty or wrong results because Readwise articles without a `published_date` field have NULL in `published_at`.
**Why it happens:** Readwise API returns `published_date: null` for many sources (self-published, newsletters, PDFs).
**How to avoid:** For STR-03, document this in tests. Temporal queries must handle NULL gracefully. Use `ingested_at` as fallback for articles without `published_at`.
**Warning signs:** `SELECT count(*) FROM sources WHERE published_at IS NULL` returns a high fraction of total sources.

### Pitfall 6: Summary Regeneration Timing
**What goes wrong:** Topic summary is regenerated after each individual article assignment during a batch sync, causing N LLM calls for N new articles in the same topic.
**Why it happens:** Naive per-article trigger.
**How to avoid:** Collect all topic_ids that received new members during a sync run, then regenerate summaries once per changed topic at the end.
**Warning signs:** Sync time scales linearly with article count; cost is O(N_articles) LLM calls instead of O(N_changed_topics).

---

## Code Examples

Verified patterns from official sources and project codebase:

### Integrate Clustering into the Sync Command
```python
# cli.py — extend the sync command (after Step 3: chunk/embed)
# Lazy import follows existing pattern
from second_brain.ingestion.clustering import assign_topics_to_source

# After storing chunks for new_source_id:
changed_topic_ids = set()
for source_id in newly_stored_source_ids:
    topic_id = assign_topics_to_source(source_id, db, embed_provider, llm_provider)
    if topic_id:
        changed_topic_ids.add(topic_id)

# Regenerate summaries only for topics that changed
for topic_id in changed_topic_ids:
    summary = regenerate_topic_summary(topic_id, db, llm_provider)
    db.table("topics").update({"summary": summary}).eq("id", topic_id).execute()
```

### Cosine Similarity via pgvector (SQL approach, alternative to numpy)
```sql
-- Source: supabase.com/docs/guides/ai/semantic-search
-- 1 - distance = similarity for normalized vectors
SELECT id, name, 1 - (centroid_embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM topics
WHERE centroid_embedding IS NOT NULL
ORDER BY centroid_embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 3;
```

### Supabase RPC for match_topic
```python
# Source: existing db.rpc() pattern from retrieval/search.py
response = db.rpc(
    "match_topic",
    {
        "query_embedding": source_embedding,  # list[float]
        "match_threshold": 0.65,
        "match_count": 1,
    },
).execute()
if response.data:
    best_topic_id = response.data[0]["topic_id"]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LDA / NMF bag-of-words topic modeling | Embedding-based centroid clustering + LLM labeling | 2022-2023 | Better semantic coherence; human-readable names |
| BERTopic batch HDBSCAN | BERTopic online (.partial_fit with MiniBatchKMeans) | 2023 | Incremental updates possible but complex |
| k-means (fixed k) | Density/threshold approaches (dynamic k) | 2021+ | No need to specify k; handles growing corpora |
| Keyword-based topic names | LLM-generated topic names | 2023+ | More interpretable for personal knowledge use |

**Deprecated/outdated:**
- **LDA (Latent Dirichlet Allocation):** Bag-of-words; ignores semantic meaning of embeddings. Replaced by BERTopic and embedding-based approaches for 2024+ systems.
- **HDBSCAN full re-cluster on incremental data:** Documented limitation in BERTopic discussions (2025). Not suitable for systems where topic IDs must remain stable.

---

## Open Questions

1. **Similarity threshold (0.65 recommended)**
   - What we know: Supabase docs show match_threshold in 0.7-0.8 range for retrieval; clustering benefits from lower threshold (0.60-0.70) to allow broader topic membership
   - What's unclear: Optimal threshold depends on the embedding model; text-embedding-3-small (1536-dim) tends to produce higher cosine similarities than shorter models
   - Recommendation: Start at 0.65, log similarity scores during first sync, adjust if topics are too coarse (raise to 0.70) or too fragmented (lower to 0.60)

2. **How should Phase 3 handle rows where `sources.source_embedding` is still NULL?**
   - What we know: New inserts already store `sources.source_embedding`, and Phase 3 should use that existing column as its source-level vector
   - What's unclear: Whether the remaining older NULL rows need a backfill before clustering is enabled across the whole corpus
   - Recommendation: Treat NULL coverage as an explicit repair/backfill decision. Do not reintroduce a second `sources.embedding` field or switch the design back to chunk-averaging because older plan text said so.

3. **Topics API endpoint for Phase 4**
   - What we know: Phase 4 (Synthesis) will need to query topics to build synthesis context
   - What's unclear: Whether Phase 4 needs topics exposed via a FastAPI route or queries them internally
   - Recommendation: Add `GET /api/topics` returning topic list with name + summary. Plan this in Phase 3 to avoid Phase 4 plan backtracking.

4. **Temporal fallback for NULL published_at**
   - What we know: Many Readwise articles lack `published_date` in API response
   - What's unclear: How large this fraction is for the user's specific corpus
   - Recommendation: For STR-03, use `COALESCE(published_at, ingested_at)` in temporal queries so articles without a publication date still participate in time-range analysis, using their ingestion date as a proxy.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in pyproject.toml dev deps) |
| Config file | `backend/pyproject.toml` (no pytest.ini; pytest picks up `tests/`) |
| Quick run command | `cd backend && python -m pytest tests/clustering/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STR-01 | New article gets assigned to matching topic when similarity >= threshold | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_assign_to_existing_topic -x` | Wave 0 |
| STR-01 | New article creates new topic when no existing topic clears threshold | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_create_new_topic -x` | Wave 0 |
| STR-01 | source_topics row created after assignment | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_source_topics_row_created -x` | Wave 0 |
| STR-02 | Topic summary is updated after new source joins | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_summary_regenerated -x` | Wave 0 |
| STR-02 | Batch sync only calls LLM once per changed topic, not per article | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_summary_deduplication -x` | Wave 0 |
| STR-03 | get_topic_sources_by_date filters correctly on published_at | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_temporal_filter -x` | Wave 0 |
| STR-03 | COALESCE(published_at, ingested_at) used when published_at is NULL | unit | `cd backend && python -m pytest tests/clustering/test_clustering.py::test_temporal_null_fallback -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/clustering/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/clustering/__init__.py` — new test package
- [ ] `backend/tests/clustering/test_clustering.py` — covers all STR-xx tests above with mocked DB + LLM
- [ ] `backend/second_brain/ingestion/clustering.py` — implementation module (Wave 1 creates this)

*(All tests use `unittest.mock.patch` and `MagicMock` consistent with existing test patterns in `tests/chat/`)*

---

## Sources

### Primary (HIGH confidence)
- Supabase official docs (supabase.com/docs/guides/ai/semantic-search) — match_threshold pattern, cosine distance vs. similarity clarification
- Supabase official docs (supabase.com/docs/guides/database/extensions/pgvector) — pgvector AVG() for centroids, vector column syntax
- BERTopic official docs (maartengr.github.io/BERTopic/getting_started/online/online.html) — incremental clustering limitations, partial_fit constraints
- Project schema.sql — confirmed topics, source_topics, sources.published_at all exist; identified missing centroid_embedding column

### Secondary (MEDIUM confidence)
- [BERTopic GitHub Discussion #2119](https://github.com/MaartenGr/BERTopic/discussions/2119) — production limitations of partial_fit; merge_models as alternative
- [Online Density-Based Clustering paper (arxiv 2601.20680)](https://arxiv.org/html/2601.20680) — confirms HDBSCAN cannot support incremental updates; O(NlogN) re-computation required
- [Comparing LLM-Based vs Traditional Clustering (chrisellis.dev)](https://www.chrisellis.dev/articles/comparing-llm-based-vs-traditional-clustering-for-support-conversations) — LLM approach vs HDBSCAN tradeoffs

### Tertiary (LOW confidence)
- machinelearningplus.com — cosine similarity numpy patterns (standard practice, not novel finding)
- Various Medium/TDS articles on BERTopic + UMAP + HDBSCAN pipeline — confirmed complexity relative to project needs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies needed beyond numpy; all LLM/DB patterns already in codebase
- Schema changes: HIGH — confirmed via direct schema.sql read; `sources.source_embedding` already exists, so the remaining additions are minimal (`topics.centroid_embedding` + optional `match_topic`)
- Architecture: HIGH — centroid-threshold approach is well-understood; patterns verified against project conventions
- HDBSCAN unsuitability: HIGH — confirmed by BERTopic official docs and arxiv paper that incremental update is not supported
- Similarity threshold (0.65): MEDIUM — reasonable starting point verified against Supabase docs range; must be tuned per corpus
- Pitfalls: HIGH — derived from official docs + project-specific constraints

**Research date:** 2026-03-10
**Valid until:** 2026-06-10 (90 days; embedding models and pgvector API are stable)

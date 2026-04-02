"""
cli.py — Second Brain CLI entry point

Defines the Typer application and all CLI commands.

Commands:
    sync   — fetch articles from Readwise Reader, store and embed them
    query  — search the knowledge base semantically and by keyword

Entry points:
    python -m second_brain sync           # run as Python module
    python -m second_brain query "..."    # run as Python module
    second-brain sync                     # run via installed script (pyproject.toml)
    second-brain query "..."              # run via installed script

Design notes:
    - Uses `rich` for styled output (bold text, color, rules).
    - Each stage prints progress so the user can see what is happening.
    - `--limit` flag makes testing cheap — no need to process 1000 articles.
    - Heavy imports are deferred inside command functions (lazy-import pattern)
      so that `--help` is always instantaneous.

Note: Readwise pagination must use pageCursor correctly — see readwise.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.rule import Rule

app = typer.Typer(help="Second Brain CLI — sync and query your knowledge base")
console = Console()


# =============================================================================
# sync command
# =============================================================================

@app.command()
def sync(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Max articles to process (useful for testing without a full sync)",
    )
) -> None:
    """
    Sync all articles from Readwise Reader into the database.

    Steps:
        1. Fetch all articles from the Readwise API (paginated).
        2. Store new articles in the `sources` table with one source-level embedding.
        3. For each new article: chunk the text, generate chunk embeddings, store in `chunks`.
        4. Print a summary of what was done.

    Requires environment variables:
        READWISE_TOKEN      — Readwise API token
        SUPABASE_URL        — Supabase project URL
        SUPABASE_KEY        — Supabase anon or service key
        OPENROUTER_API_KEY  — OpenRouter API key (for embeddings)
    """
    # Import here to avoid slow startup time for `--help` invocations.
    # These imports trigger config loading and dependency setup.
    from second_brain.config import cfg
    from second_brain.db import get_db_client
    from second_brain.providers.embeddings import get_embedding_provider
    from second_brain.ingestion.readwise import (
        chunk_new_sources,
        fetch_all_articles,
        get_last_ingested_at,
        store_articles,
    )

    console.print("[bold]Starting Readwise sync...[/bold]")

    # -------------------------------------------------------------------------
    # Step 1: Fetch new articles from Readwise Reader (incremental)
    # -------------------------------------------------------------------------
    console.print("\n[cyan]Step 1:[/cyan] Fetching articles from Readwise Reader...")

    db = get_db_client()
    embed_provider = get_embedding_provider()

    updated_after = get_last_ingested_at(db)
    if updated_after:
        console.print(f"  Incremental sync — fetching articles updated after [bold]{updated_after}[/bold]")
    else:
        console.print("  First run — fetching full corpus.")

    articles = fetch_all_articles(cfg.readwise.token, updated_after=updated_after)
    console.print(f"  Fetched [bold]{len(articles)}[/bold] articles total.")

    # Optional: limit the number of articles processed (for testing)
    if limit is not None:
        articles = articles[:limit]
        console.print(f"  [yellow]Limit set to {limit} — processing {len(articles)} articles.[/yellow]")

    # -------------------------------------------------------------------------
    # Step 2: Store new articles (skip existing ones by readwise_id)
    # -------------------------------------------------------------------------
    console.print("\n[cyan]Step 2:[/cyan] Storing articles and source embeddings...")

    new_count, skipped_count, new_source_ids = store_articles(articles, db, embed_provider=embed_provider)
    console.print(f"  [green]{new_count} new[/green] articles stored, [yellow]{skipped_count} skipped[/yellow] (already in DB).")

    # -------------------------------------------------------------------------
    # Step 3: Chunk only the newly inserted articles.
    # -------------------------------------------------------------------------
    total_chunks = 0
    if new_source_ids:
        console.print("\n[cyan]Step 3:[/cyan] Chunking and embedding new articles...")
        total_chunks = chunk_new_sources(
            new_source_ids,
            db,
            embed_provider,
            target_tokens=cfg.chunking.target_tokens,
            overlap_tokens=cfg.chunking.overlap_tokens,
        )
        console.print(f"  {total_chunks} chunks created across {len(new_source_ids)} new articles.")
    else:
        console.print("\n[cyan]Step 3:[/cyan] No new articles — skipping chunking.")

    # -------------------------------------------------------------------------
    # Step 4: Assign new articles to topics
    # -------------------------------------------------------------------------
    if new_source_ids:
        try:
            console.print("\n[cyan]Step 4:[/cyan] Assigning articles to topics...")
            from second_brain.ingestion.clustering import assign_topic_to_source
            from second_brain.providers.llm import get_llm_provider
            llm_provider = get_llm_provider()

            changed_topic_ids: set[str] = set()
            for source_id in new_source_ids:
                result = assign_topic_to_source(source_id, db, llm_provider)
                if result.topic_id:
                    changed_topic_ids.add(result.topic_id)
                    status = "new topic" if result.created_topic else f"→ existing (sim={result.similarity:.2f})"
                    console.print(f"  [dim]{source_id[:8]}[/dim]: {status}")

            # -------------------------------------------------------------------------
            # Step 5: Regenerate summaries for any topics that gained new members
            # -------------------------------------------------------------------------
            if changed_topic_ids:
                console.print("\n[cyan]Step 5:[/cyan] Updating topic summaries...")
                for topic_id in changed_topic_ids:
                    rows = db.table("source_topics").select("sources(title)").eq("topic_id", topic_id).execute().data or []
                    titles = [r["sources"]["title"] for r in rows if r.get("sources")][:30]
                    summary = llm_provider.complete([
                        {"role": "system", "content": "You write brief topic summaries for a personal knowledge base. 2-3 sentences max."},
                        {"role": "user", "content": "Topic sources:\n" + "\n".join(f"- {t}" for t in titles)},
                    ])
                    db.table("topics").update({"summary": summary}).eq("id", topic_id).execute()
                    console.print(f"  Updated summary for topic {topic_id[:8]}")
        except Exception as exc:
            console.print(f"\n[yellow]Warning:[/yellow] Topic assignment failed (sync still complete): {exc}")
    else:
        console.print("\n[cyan]Step 4:[/cyan] No new articles — skipping topic assignment.")

    # -------------------------------------------------------------------------
    # Step 6: Final summary
    # -------------------------------------------------------------------------
    console.print(
        f"\n[bold green]Sync complete.[/bold green] "
        f"{new_count} new articles, {skipped_count} skipped, "
        f"{total_chunks} chunks created."
    )


@app.command("backfill-source-embeddings")
def backfill_source_embeddings(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Max missing source rows to repair in this run",
    )
) -> None:
    """
    Fill missing `sources.source_embedding` values for older rows.

    Uses the same whole-source embedding logic as normal Readwise sync, but only
    updates rows where `source_embedding` is currently NULL.
    """
    from second_brain.db import get_db_client
    from second_brain.providers.embeddings import get_embedding_provider
    from second_brain.ingestion.readwise import backfill_missing_source_embeddings

    console.print("[bold]Backfilling missing source embeddings...[/bold]")
    if limit is not None:
        console.print(
            f"  [yellow]Limit set to {limit} missing rows for this run.[/yellow]"
        )

    db = get_db_client()
    embed_provider = get_embedding_provider()
    missing_count, updated_count, skipped_no_text_count = backfill_missing_source_embeddings(
        db,
        embed_provider,
        limit=limit,
    )

    if missing_count == 0:
        console.print(
            "\n[bold green]Backfill complete.[/bold green] No missing source embeddings found."
        )
        return

    console.print(
        f"\n[bold green]Backfill complete.[/bold green] "
        f"{updated_count} source embeddings written, "
        f"{skipped_no_text_count} rows skipped for missing raw text."
    )


@app.command("analyze-source")
def analyze_source_command(source_id: str) -> None:
    """
    Extract entities, claims, evidence, and links for one stored source.

    This is Phase 2's rerunnable, source-scoped analysis entrypoint.
    """
    from second_brain.analysis.extraction import analyze_source
    from second_brain.db import get_db_client
    from second_brain.providers.llm import get_llm_provider

    console.print(f"[bold]Analyzing source {source_id}...[/bold]")
    db = get_db_client()
    llm = get_llm_provider()
    result = analyze_source(source_id, db, llm)
    console.print(
        f"[bold green]Analysis complete.[/bold green] "
        f"{result['entity_count']} entities, "
        f"{result['claim_count']} claims, "
        f"{result['evidence_count']} evidence rows, "
        f"{result['link_count']} links."
    )


@app.command("repair-chunks")
def repair_chunks(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Max sources to repair in this run (useful for testing)",
    )
) -> None:
    """
    Chunk and embed any sources that have no chunks.

    Use this to recover from a crashed sync that stored articles but didn't
    finish chunking them. Safe to re-run — skips sources that already have chunks.
    """
    from second_brain.db import get_db_client
    from second_brain.providers.embeddings import get_embedding_provider
    from second_brain.config import cfg
    from second_brain.ingestion.readwise import backfill_missing_chunks

    console.print("[bold]Repairing missing chunks...[/bold]")

    db = get_db_client()
    embed_provider = get_embedding_provider()
    missing_count, repaired, total_chunks, skipped = backfill_missing_chunks(
        db,
        embed_provider,
        target_tokens=cfg.chunking.target_tokens,
        overlap_tokens=cfg.chunking.overlap_tokens,
    )

    if missing_count == 0:
        console.print("\n[bold green]Done.[/bold green] All sources already have chunks.")
        return

    console.print(
        f"\n[bold green]Done.[/bold green] "
        f"{repaired} sources repaired, {total_chunks} chunks created, "
        f"{skipped} skipped (no raw text). "
        f"({missing_count} sources were missing chunks.)"
    )


@app.command("assign-topics")
def assign_topics(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Max unassigned source rows to process in this run",
    )
) -> None:
    """
    Assign unassigned sources to existing or newly created topics.

    This is an explicit Phase 3 mechanics command. It intentionally stops before
    wiring topic assignment into normal sync or generating topic summaries.
    """
    from second_brain.db import get_db_client
    from second_brain.ingestion.clustering import assign_topics_to_unassigned_sources
    from second_brain.providers.llm import get_llm_provider

    console.print("[bold]Assigning topics to unassigned sources...[/bold]")
    if limit is not None:
        console.print(
            f"  [yellow]Limit set to {limit} unassigned sources for this run.[/yellow]"
        )

    db = get_db_client()
    llm_provider = get_llm_provider()
    result = assign_topics_to_unassigned_sources(
        db,
        llm_provider,
        limit=limit,
    )

    if result.processed_count == 0:
        console.print(
            "\n[bold green]Topic assignment complete.[/bold green] No unassigned sources found."
        )
        return

    console.print(
        f"\n[bold green]Topic assignment complete.[/bold green] "
        f"{result.assigned_existing_count} joined existing topics, "
        f"{result.created_topic_count} created new topics, "
        f"{result.skipped_missing_embedding_count} skipped for missing source embeddings."
    )


# =============================================================================
# query command
# =============================================================================

@app.command()
def query(
    question: str = typer.Argument(..., help="Your question or search query"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
    after: str = typer.Option(
        None,
        "--after",
        help="Filter to articles published after date (YYYY-MM-DD)",
    ),
    before: str = typer.Option(
        None,
        "--before",
        help="Filter to articles published before date (YYYY-MM-DD)",
    ),
) -> None:
    """
    Search your knowledge base semantically and by keyword.

    Uses hybrid search: 70% pgvector cosine similarity + 30% PostgreSQL FTS.
    Results are ranked by hybrid_score (highest first).

    Examples:
        second-brain query "what do I think about AI safety?"
        second-brain query "machine learning" --top-k 10
        second-brain query "AI" --after 2024-01-01
        second-brain query "AI" --before 2024-12-31
    """
    # Import here (lazy) — keeps --help instantaneous; heavy imports only
    # when the query command is actually executed.
    from second_brain.retrieval.search import hybrid_search

    console.print(f"[bold]Searching for:[/bold] {question}")

    # Validate date filters — after/before accept YYYY-MM-DD and are passed
    # as-is to the SQL function which casts them to the `date` type for
    # published_at comparisons.
    for flag_name, date_str in [("--after", after), ("--before", before)]:
        if date_str is not None:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise typer.BadParameter(
                    f"'{date_str}' is not a valid date. Use YYYY-MM-DD format (e.g. 2024-03-15).",
                    param_hint=flag_name,
                )

    # Run the hybrid search query
    results = hybrid_search(query=question, top_k=top_k, after=after, before=before)

    if not results:
        console.print(
            "[yellow]No results found. Try a different query or sync more articles.[/yellow]"
        )
        return

    # Print one formatted card per result
    for i, result in enumerate(results, start=1):
        console.print(Rule())
        console.print(
            f"[bold]Result {i}[/bold]  |  "
            f"Score: [green]{result.hybrid_score:.3f}[/green]  "
            f"(vector: {result.vector_score:.3f}, fts: {result.fts_score:.3f})"
        )
        console.print(f"[bold]Title:[/bold]    {result.title}")
        console.print(f"[bold]Author:[/bold]   {result.author or '—'}")
        console.print(f"[bold]URL:[/bold]      {result.url or '—'}")
        console.print(f"[bold]Date:[/bold]     {result.published_at or '—'}")
        console.print("")

        # Truncate long chunks for readable terminal output
        chunk_preview = (
            result.content[:300] + "..." if len(result.content) > 300 else result.content
        )
        console.print(f'"{chunk_preview}"')

    console.print(Rule())
    console.print(f"\n[dim]Showing {len(results)} of top {top_k} results[/dim]")


# =============================================================================
# Module entry point
# =============================================================================

if __name__ == "__main__":
    # Supports: python -m second_brain
    app()

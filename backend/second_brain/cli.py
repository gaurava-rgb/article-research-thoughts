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
        2. Store new articles in the `sources` table (skip duplicates by readwise_id).
        3. For each new article: chunk the text, generate embeddings, store in `chunks`.
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
    from second_brain.ingestion.readwise import fetch_all_articles, store_articles
    from second_brain.ingestion.chunker import chunk_text, store_chunks_with_embeddings

    console.print("[bold]Starting Readwise sync...[/bold]")

    # -------------------------------------------------------------------------
    # Step 1: Fetch all articles from Readwise Reader
    # -------------------------------------------------------------------------
    console.print("\n[cyan]Step 1:[/cyan] Fetching articles from Readwise Reader...")

    articles = fetch_all_articles(cfg.readwise.token)
    console.print(f"  Fetched [bold]{len(articles)}[/bold] articles total.")

    # Optional: limit the number of articles processed (for testing)
    if limit is not None:
        articles = articles[:limit]
        console.print(f"  [yellow]Limit set to {limit} — processing {len(articles)} articles.[/yellow]")

    # -------------------------------------------------------------------------
    # Step 2: Store new articles (skip existing ones by readwise_id)
    # -------------------------------------------------------------------------
    console.print("\n[cyan]Step 2:[/cyan] Storing articles in database...")

    db = get_db_client()
    new_count, skipped_count = store_articles(articles, db)
    console.print(f"  [green]{new_count} new[/green] articles stored, [yellow]{skipped_count} skipped[/yellow] (already in DB).")

    if new_count == 0:
        console.print("\n[bold green]Sync complete.[/bold green] No new articles to process.")
        return

    # -------------------------------------------------------------------------
    # Step 3: Chunk and embed new articles
    # Fetch article IDs from DB so we can link chunks to sources rows.
    # -------------------------------------------------------------------------
    console.print("\n[cyan]Step 3:[/cyan] Chunking and embedding new articles...")

    embed_provider = get_embedding_provider()
    total_chunks = 0

    # We need to find only the articles that were just inserted (new ones).
    # We re-query the DB for each article by readwise_id to get its UUID.
    for article in articles:
        # Only process articles that were just inserted (not skipped)
        source_result = (
            db.table("sources")
            .select("id")
            .eq("readwise_id", article.readwise_id)
            .execute()
        )

        if not source_result.data:
            # Should not happen — we just inserted it — but be defensive
            console.print(f"  [red]Warning:[/red] Could not find source row for {article.readwise_id}")
            continue

        source_id = source_result.data[0]["id"]

        # Check if chunks already exist for this source (avoid double-processing
        # in case the embedding step was interrupted and re-run)
        existing_chunks = (
            db.table("chunks")
            .select("id")
            .eq("source_id", source_id)
            .limit(1)
            .execute()
        )
        if existing_chunks.data:
            # Already chunked (e.g. from a previous partial run)
            continue

        # Split text into ~500-token segments with ~50-token overlap
        chunks = chunk_text(
            article.text,
            source_id=str(source_id),
            target_tokens=cfg.chunking.target_tokens,
            overlap_tokens=cfg.chunking.overlap_tokens,
        )

        if not chunks:
            console.print(f"  [yellow]  Skipped (no chunks):[/yellow] {article.title[:60]}")
            continue

        # Generate embeddings and store chunks in the database
        stored = store_chunks_with_embeddings(chunks, embed_provider, db)
        total_chunks += stored

        # Print per-article progress so the user can see what's happening
        title_preview = article.title[:60] if article.title else "(no title)"
        console.print(f"  {title_preview}: {len(chunks)} chunks, {stored} embeddings")

    # -------------------------------------------------------------------------
    # Step 4: Final summary
    # -------------------------------------------------------------------------
    console.print(
        f"\n[bold green]Sync complete.[/bold green] "
        f"{new_count} new articles, {skipped_count} skipped, "
        f"{total_chunks} chunks created."
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

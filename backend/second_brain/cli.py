"""
cli.py — Second Brain CLI entry point

Defines the Typer application and all CLI commands. The main command is
`sync`, which fetches articles from Readwise Reader, stores them in Supabase,
and generates embeddings for semantic search.

Entry points:
    python -m second_brain sync           # run as Python module
    second-brain sync                     # run via installed script (pyproject.toml)

Usage:
    # Sync your entire Readwise library
    second-brain sync

    # Sync only the first 5 articles (useful for testing)
    second-brain sync --limit 5

Design notes:
    - Uses `rich` for styled output (bold text, color).
    - Each stage prints progress so the user can see what is happening.
    - `--limit` flag makes testing cheap — no need to process 1000 articles.

Note: Readwise pagination must use pageCursor correctly — see readwise.py.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

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
# Module entry point
# =============================================================================

if __name__ == "__main__":
    # Supports: python -m second_brain
    app()

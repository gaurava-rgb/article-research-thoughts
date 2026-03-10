"""
ingestion/chunker.py — Text chunking and embedding pipeline

Splits article text into overlapping segments (~500 tokens each) and stores
each segment with its embedding vector in the Supabase `chunks` table.

Why chunk at all?
    Language models and vector search work best on focused passages, not whole
    articles. Chunking lets us retrieve the specific paragraph that answers a
    question rather than entire articles. Overlap preserves context across
    chunk boundaries.

Why tiktoken?
    tiktoken counts tokens the same way OpenAI-family models do, so our
    target_tokens and overlap_tokens are accurate for the embedding model
    (openai/text-embedding-3-small). The cl100k_base encoding is shared by
    GPT-4, ChatGPT, and text-embedding-3-*.

Usage:
    from second_brain.ingestion.chunker import chunk_text, store_chunks_with_embeddings

    chunks = chunk_text(article.text, source_id="uuid-from-sources-table")
    stored = store_chunks_with_embeddings(chunks, get_embedding_provider(), db)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import tiktoken

if TYPE_CHECKING:
    import supabase
    from second_brain.providers.embeddings import EmbeddingProvider


# =============================================================================
# Data model
# =============================================================================

@dataclass
class Chunk:
    """
    Represents one text segment of a source article.

    source_id links back to the UUID primary key in the `sources` table.
    chunk_index is 0-based and sequential within one article.
    token_count reflects actual tokens counted by tiktoken.
    """
    source_id: str      # UUID from sources table (foreign key)
    chunk_index: int    # 0, 1, 2 ... within this article
    content: str        # The text of this chunk
    token_count: int    # Actual token count (via tiktoken)


# =============================================================================
# Sentence splitter
# =============================================================================

# Regex for sentence boundary detection.
# Splits on ". ", "! ", "? ", and double newlines.
# This avoids cutting in the middle of a sentence — important for coherent
# embedding representations.
_SENTENCE_SPLIT_PATTERN = re.compile(r'(?<=[.!?])\s+|\n\n+')


def _split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation heuristics.

    This is intentionally simple — a real NLP sentence tokeniser is overkill
    for chunking. The goal is to avoid mid-sentence splits, not perfect parsing.

    Args:
        text: Any plaintext string.

    Returns:
        List of sentence-like strings (may include fragments).
    """
    parts = _SENTENCE_SPLIT_PATTERN.split(text)
    # Filter out empty strings that can arise from consecutive delimiters
    return [p.strip() for p in parts if p.strip()]


# =============================================================================
# Chunking
# =============================================================================

# Minimum tokens in a chunk to be worth keeping.
# Very short chunks (e.g. a single word) add noise to the vector index.
MIN_CHUNK_TOKENS = 20

# The tiktoken encoding used by OpenAI text-embedding-3-* models and GPT-4.
_ENCODING_NAME = "cl100k_base"


def chunk_text(
    text: str,
    source_id: str,
    target_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """
    Split text into overlapping chunks of approximately target_tokens each.

    Algorithm:
        1. Split text into sentences to avoid mid-sentence cuts.
        2. Accumulate sentences into a buffer until it hits target_tokens.
        3. When full, save the buffer as a Chunk, then start a new buffer
           seeded with the last overlap_tokens tokens of the current chunk
           (for context continuity across chunk boundaries).
        4. Flush any remaining text as a final chunk.
        5. Drop chunks shorter than MIN_CHUNK_TOKENS.

    Args:
        text:          Plain text to chunk.
        source_id:     UUID from the sources table — links chunk back to article.
        target_tokens: Desired token size per chunk (default 500).
        overlap_tokens: Tokens to repeat at the start of each new chunk (default 50).

    Returns:
        List of Chunk dataclasses, sequentially indexed from 0.
    """
    enc = tiktoken.get_encoding(_ENCODING_NAME)

    sentences = _split_into_sentences(text)

    chunks: list[Chunk] = []
    chunk_index = 0

    # Current accumulation buffer (list of sentence strings)
    buffer: list[str] = []
    buffer_tokens: int = 0

    # Tokens from the tail of the previous chunk, used to seed the next buffer
    # for overlap. Stored as a decoded string for simplicity.
    overlap_seed: str = ""

    for sentence in sentences:
        sentence_tokens = len(enc.encode(sentence))

        # If adding this sentence would exceed the target, flush the buffer
        if buffer_tokens + sentence_tokens > target_tokens and buffer:
            chunk_text_content = overlap_seed + " ".join(buffer) if overlap_seed else " ".join(buffer)
            chunk_tokens = len(enc.encode(chunk_text_content))

            if chunk_tokens >= MIN_CHUNK_TOKENS:
                chunks.append(Chunk(
                    source_id=source_id,
                    chunk_index=chunk_index,
                    content=chunk_text_content,
                    token_count=chunk_tokens,
                ))
                chunk_index += 1

            # Compute the overlap seed: take the last overlap_tokens tokens
            # from the chunk we just saved and decode back to text.
            full_tokens = enc.encode(chunk_text_content)
            if len(full_tokens) > overlap_tokens:
                overlap_seed = enc.decode(full_tokens[-overlap_tokens:])
            else:
                overlap_seed = chunk_text_content

            # Reset buffer with the current sentence
            buffer = [sentence]
            buffer_tokens = sentence_tokens
        else:
            # Sentence fits — keep accumulating
            buffer.append(sentence)
            buffer_tokens += sentence_tokens

    # Flush the remaining buffer as a final chunk
    if buffer:
        chunk_text_content = overlap_seed + " ".join(buffer) if overlap_seed else " ".join(buffer)
        chunk_tokens = len(enc.encode(chunk_text_content))

        if chunk_tokens >= MIN_CHUNK_TOKENS:
            chunks.append(Chunk(
                source_id=source_id,
                chunk_index=chunk_index,
                content=chunk_text_content,
                token_count=chunk_tokens,
            ))

    return chunks


# =============================================================================
# Embedding + storage pipeline
# =============================================================================

def store_chunks_with_embeddings(
    chunks: list[Chunk],
    embed_provider: "EmbeddingProvider",
    db: "supabase.Client",
) -> int:
    """
    Generate embeddings for all chunks and insert them into the `chunks` table.

    Batching:
        We call embed_provider.embed() in batches of 100 to respect rate limits.
        OpenRouter (and OpenAI) have per-request input limits. 100 texts per
        call is well within those limits.

    Args:
        chunks:         List of Chunk instances (from chunk_text).
        embed_provider: An EmbeddingProvider instance (from get_embedding_provider()).
        db:             Supabase client (from get_db_client()).

    Returns:
        Total number of chunks inserted into the database.
    """
    if not chunks:
        return 0

    BATCH_SIZE = 100

    # Extract just the text content for embedding
    chunk_texts = [chunk.content for chunk in chunks]

    # Collect all embeddings, batching to stay within rate limits
    all_embeddings: list[list[float]] = []
    for batch_start in range(0, len(chunk_texts), BATCH_SIZE):
        batch = chunk_texts[batch_start : batch_start + BATCH_SIZE]
        batch_embeddings = embed_provider.embed(batch)
        all_embeddings.extend(batch_embeddings)

    # Insert each chunk with its corresponding embedding vector.
    # Supabase's pgvector extension accepts Python lists of floats directly.
    inserted_count = 0
    for chunk, embedding in zip(chunks, all_embeddings):
        db.table("chunks").insert({
            "source_id": chunk.source_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "embedding": embedding,
        }).execute()
        inserted_count += 1

    return inserted_count

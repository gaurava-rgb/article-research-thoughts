"""
providers/embeddings.py — Embedding provider abstraction

Defines the EmbeddingProvider interface and concrete implementations.
Use get_embedding_provider() to get the right provider based on config.yaml.

Usage:
    from second_brain.providers.embeddings import get_embedding_provider

    provider = get_embedding_provider()
    vectors = provider.embed(["Some text to embed", "Another text"])
    # vectors is a list of lists of floats, one per input text

Why abstraction?
    If you switch from OpenRouter to a local embedding model tomorrow,
    you change one line in config.yaml (embeddings.provider) and add
    a new class here. No other code changes.
"""

import logging
import re
import time
from abc import ABC, abstractmethod
from typing import List

import openai

from second_brain.config import cfg

logger = logging.getLogger(__name__)


# =============================================================================
# Abstract base class
# =============================================================================

class EmbeddingProvider(ABC):
    """
    Abstract base class for all embedding providers.

    Any class that generates text embeddings must implement this interface.
    This ensures all providers are interchangeable in the rest of the codebase.
    """

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Convert a list of strings into embedding vectors.

        Args:
            texts: List of strings to embed. Can contain one or many items.

        Returns:
            List of embedding vectors, one per input text.
            Each vector is a list of floats (length = model dimension, e.g. 1536).

        Example:
            vectors = provider.embed(["hello world"])
            # vectors[0] is a list of 1536 floats
        """
        ...


# =============================================================================
# OpenRouter implementation
# =============================================================================

class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider backed by OpenRouter's API.

    OpenRouter is OpenAI-compatible, so we use the `openai` Python library
    pointed at OpenRouter's base URL. This means you can use any embedding
    model available on OpenRouter (e.g. openai/text-embedding-3-small).

    Batching:
        OpenRouter has rate limits. We send texts in batches of 100 to avoid
        hitting those limits. Results are reassembled in the original order.
    """

    # Maximum number of texts to send in a single API request.
    # 20 is conservative for OpenRouter — large batches can return empty data.
    BATCH_SIZE = 20

    # Retry settings for transient API failures (connection errors, rate limits).
    MAX_RETRIES = 5
    RETRY_DELAY = 2.0  # seconds, doubles on each retry (max ~32s on attempt 5)

    def __init__(self):
        """
        Initialize the OpenRouter client using settings from config.yaml.

        cfg.embeddings.api_key  — resolved from OPENROUTER_API_KEY env var
        cfg.embeddings.base_url — https://openrouter.ai/api/v1
        cfg.embeddings.model    — e.g. "openai/text-embedding-3-small"
        """
        self._client = openai.OpenAI(
            api_key=cfg.embeddings.api_key,
            base_url=cfg.embeddings.base_url,
        )
        self._model = cfg.embeddings.model

    # Control characters except tab, newline, carriage return (which are fine in text).
    _CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

    def _sanitize(self, text: str) -> str:
        """Strip control characters that can cause embedding APIs to return empty data."""
        return self._CONTROL_CHARS.sub('', text).strip()

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts, batching into groups of BATCH_SIZE.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors in the same order as the input texts.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        # Split texts into batches and embed each batch
        for batch_start in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[batch_start : batch_start + self.BATCH_SIZE]

            # Sanitize: strip control characters. If a text becomes empty after
            # sanitization, replace with a single space so the index stays aligned.
            clean_batch = [self._sanitize(t) or " " for t in batch]

            delay = self.RETRY_DELAY
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = self._client.embeddings.create(
                        model=self._model,
                        input=clean_batch,
                    )
                    break  # success
                except (ValueError, openai.APIError) as exc:
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(
                            "Embedding batch failed (attempt %d/%d): %s — "
                            "batch size=%d, first text (truncated): %r",
                            attempt + 1, self.MAX_RETRIES, exc,
                            len(clean_batch), clean_batch[0][:120],
                        )
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(
                            "Embedding batch failed after %d attempts. "
                            "batch size=%d, texts (truncated): %r",
                            self.MAX_RETRIES, len(clean_batch),
                            [t[:80] for t in clean_batch],
                        )
                        raise

            # The API returns embeddings in the same order as the input.
            # Sort by index to be safe (the spec allows out-of-order responses).
            batch_embeddings = sorted(response.data, key=lambda e: e.index)
            all_embeddings.extend([e.embedding for e in batch_embeddings])

        return all_embeddings


# =============================================================================
# Factory function
# =============================================================================

def get_embedding_provider() -> EmbeddingProvider:
    """
    Return the correct EmbeddingProvider based on config.yaml.

    Reads cfg.embeddings.provider and returns the matching implementation.
    To add a new provider: add a new class above and a new branch here.

    Returns:
        An EmbeddingProvider instance ready to use.

    Raises:
        ValueError: If cfg.embeddings.provider names an unknown provider.

    Example:
        provider = get_embedding_provider()
        vectors = provider.embed(["Hello, world!"])
    """
    provider_name = cfg.embeddings.provider

    if provider_name == "openrouter":
        return OpenRouterEmbeddingProvider()

    raise ValueError(
        f"Unknown embedding provider: '{provider_name}'. "
        f"Supported providers: openrouter. "
        f"Check the embeddings.provider field in config.yaml."
    )

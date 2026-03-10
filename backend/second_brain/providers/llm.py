"""
providers/llm.py — LLM provider abstraction

Defines the LLMProvider interface and concrete implementations.
Use get_llm_provider() to get the right provider based on config.yaml.

Usage:
    from second_brain.providers.llm import get_llm_provider

    provider = get_llm_provider()
    answer = provider.complete([
        {"role": "user", "content": "What is a second brain?"}
    ])
    print(answer)  # The model's text response

Why abstraction?
    If you switch from Claude Sonnet to GPT-4o tomorrow, you change one line
    in config.yaml (llm.model) and nothing else. If you add a new provider
    (e.g. Anthropic direct), you add one class here and one branch in the
    factory. No callers change.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

import openai

from second_brain.config import cfg


# =============================================================================
# Abstract base class
# =============================================================================

class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Any class that generates text completions must implement this interface.
    This ensures all providers are interchangeable in the rest of the codebase.
    """

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Generate a text completion for the given conversation messages.

        Args:
            messages: List of message dicts in OpenAI format:
                      [{"role": "user", "content": "your question"},
                       {"role": "assistant", "content": "previous response"},
                       ...]
                      Roles must be "user", "assistant", or "system".
            **kwargs: Additional parameters passed to the underlying API
                      (e.g. temperature, max_tokens).

        Returns:
            The model's response as a plain string.

        Example:
            response = provider.complete([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Summarize this article..."},
            ])
        """
        ...


# =============================================================================
# OpenRouter implementation
# =============================================================================

class OpenRouterLLMProvider(LLMProvider):
    """
    LLM provider backed by OpenRouter's API.

    OpenRouter is OpenAI-compatible, so we use the `openai` Python library
    pointed at OpenRouter's base URL. This gives access to Claude, GPT-4o,
    Gemini, and other models through a single API and API key.

    The model is configured in config.yaml (llm.model).
    To switch models, change that field — no code changes needed.
    """

    def __init__(self):
        """
        Initialize the OpenRouter client using settings from config.yaml.

        cfg.llm.api_key  — resolved from OPENROUTER_API_KEY env var
        cfg.llm.base_url — https://openrouter.ai/api/v1
        cfg.llm.model    — e.g. "anthropic/claude-sonnet-4-5"
        """
        self._client = openai.OpenAI(
            api_key=cfg.llm.api_key,
            base_url=cfg.llm.base_url,
        )
        self._model = cfg.llm.model

    def complete(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Send messages to OpenRouter and return the model's text response.

        Args:
            messages: Conversation history in OpenAI format.
            **kwargs: Forwarded to the chat.completions.create() call.
                      Common options: temperature (0.0–2.0), max_tokens.

        Returns:
            The model's response text as a string.

        Raises:
            openai.APIError: If the API call fails (network error, rate limit, etc.)
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            **kwargs,
        )
        # choices[0].message.content is the text of the first (and usually only) response
        return response.choices[0].message.content


# =============================================================================
# Factory function
# =============================================================================

def get_llm_provider() -> LLMProvider:
    """
    Return the correct LLMProvider based on config.yaml.

    Reads cfg.llm.provider and returns the matching implementation.
    To add a new provider: add a new class above and a new branch here.

    Returns:
        An LLMProvider instance ready to use.

    Raises:
        ValueError: If cfg.llm.provider names an unknown provider.

    Example:
        provider = get_llm_provider()
        answer = provider.complete([{"role": "user", "content": "Hello!"}])
    """
    provider_name = cfg.llm.provider

    if provider_name == "openrouter":
        return OpenRouterLLMProvider()

    raise ValueError(
        f"Unknown LLM provider: '{provider_name}'. "
        f"Supported providers: openrouter. "
        f"Check the llm.provider field in config.yaml."
    )

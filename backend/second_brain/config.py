"""
config.py — Typed configuration loader

Reads config.yaml from the project root at import time and exposes a
module-level singleton `cfg`. All code imports `cfg` to get provider
settings, database credentials, and chunking parameters.

Usage:
    from second_brain.config import cfg

    print(cfg.llm.provider)       # "openrouter"
    print(cfg.llm.model)          # "anthropic/claude-sonnet-4-5"
    print(cfg.chunking.target_tokens)  # 500

How env var resolution works:
    Any config field ending in `_env` is treated as an environment variable
    name. The loader reads os.environ[that_name] and stores the resolved
    value under the same key without the `_env` suffix.

    Example: llm.api_key_env = "OPENROUTER_API_KEY"
             → cfg.llm.api_key = os.environ["OPENROUTER_API_KEY"]
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - safe fallback for serverless envs using platform vars
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False

# Load .env from the project root (walk up from this file to find it)
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)
else:
    # Also check one more level up (monorepo root)
    _env_path2 = _env_path.parent.parent / ".env"
    if _env_path2.exists():
        load_dotenv(_env_path2, override=True)


# =============================================================================
# Dataclasses — mirrors the structure of config.yaml
# =============================================================================

@dataclass
class LLMConfig:
    """Settings for the language model provider."""
    provider: str       # e.g. "openrouter"
    model: str          # e.g. "anthropic/claude-sonnet-4-5"
    api_key: str        # resolved from api_key_env
    base_url: str       # e.g. "https://openrouter.ai/api/v1"


@dataclass
class EmbeddingsConfig:
    """Settings for the text embedding provider."""
    provider: str       # e.g. "openrouter"
    model: str          # e.g. "openai/text-embedding-3-small"
    api_key: str        # resolved from api_key_env
    base_url: str       # e.g. "https://openrouter.ai/api/v1"


@dataclass
class DatabaseConfig:
    """Supabase connection settings."""
    url: str            # resolved from url_env — Supabase project URL
    key: str            # resolved from key_env — Supabase anon or service key


@dataclass
class ReadwiseConfig:
    """Readwise API settings."""
    token: str          # resolved from token_env


@dataclass
class ChunkingConfig:
    """Text chunking parameters."""
    target_tokens: int  # target number of tokens per chunk (default 500)
    overlap_tokens: int # tokens to overlap between adjacent chunks (default 50)


@dataclass
class AppConfig:
    """Root config object — holds all sub-configs."""
    llm: LLMConfig
    embeddings: EmbeddingsConfig
    database: DatabaseConfig
    readwise: ReadwiseConfig
    chunking: ChunkingConfig


# =============================================================================
# Helpers
# =============================================================================

def _resolve_env(var_name: str) -> str:
    """
    Read an environment variable by name and return its value.
    Raises RuntimeError with a helpful message if the variable is not set.
    """
    value = os.environ.get(var_name)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable: {var_name}\n"
            f"  Set it in your shell:  export {var_name}='your-value-here'"
        )
    return value


def _find_config_path() -> Path:
    """
    Locate config.yaml by:
    1. Checking CONFIG_PATH environment variable (useful for tests).
    2. Walking up from this file's directory until config.yaml is found.

    Raises FileNotFoundError if config.yaml cannot be located.
    """
    # Allow tests or CI to override the config location
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # Walk up from this file's location to find config.yaml at the project root
    current = Path(__file__).resolve().parent
    for _ in range(10):  # avoid infinite loop; project roots are at most 10 levels up
        candidate = current / "config.yaml"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    raise FileNotFoundError(
        "Could not find config.yaml. "
        "Make sure you are running from the project root, "
        "or set the CONFIG_PATH environment variable."
    )


# =============================================================================
# Loader
# =============================================================================

def _load_config() -> AppConfig:
    """
    Parse config.yaml and return a fully resolved AppConfig.

    Resolution steps:
    - Load YAML from the project root config.yaml.
    - For each field ending in `_env`, read the named env var and store
      the value under the key without the `_env` suffix.
    """
    config_path = _find_config_path()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # --- LLM ---
    llm_raw = raw["llm"]
    llm = LLMConfig(
        provider=llm_raw["provider"],
        model=llm_raw["model"],
        api_key=_resolve_env(llm_raw["api_key_env"]),
        base_url=llm_raw["base_url"],
    )

    # --- Embeddings ---
    emb_raw = raw["embeddings"]
    embeddings = EmbeddingsConfig(
        provider=emb_raw["provider"],
        model=emb_raw["model"],
        api_key=_resolve_env(emb_raw["api_key_env"]),
        base_url=emb_raw["base_url"],
    )

    # --- Database ---
    db_raw = raw["database"]
    database = DatabaseConfig(
        url=_resolve_env(db_raw["url_env"]),
        key=_resolve_env(db_raw["key_env"]),
    )

    # --- Readwise ---
    rw_raw = raw["readwise"]
    readwise = ReadwiseConfig(
        token=_resolve_env(rw_raw["token_env"]),
    )

    # --- Chunking ---
    ch_raw = raw["chunking"]
    chunking = ChunkingConfig(
        target_tokens=ch_raw["target_tokens"],
        overlap_tokens=ch_raw["overlap_tokens"],
    )

    return AppConfig(
        llm=llm,
        embeddings=embeddings,
        database=database,
        readwise=readwise,
        chunking=chunking,
    )


# =============================================================================
# Module-level singleton
# =============================================================================

# `cfg` is loaded once when this module is first imported.
# All other modules do: from second_brain.config import cfg
cfg: AppConfig = _load_config()

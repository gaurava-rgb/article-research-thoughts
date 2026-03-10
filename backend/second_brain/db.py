"""
db.py — Database connection helper

Provides a thin wrapper around the Supabase Python client.
The client is created from config (config.yaml) or environment variables as fallback.

Usage:
    from second_brain.db import get_db_client

    client = get_db_client()
    result = client.table("sources").select("*").execute()
"""

import os
from functools import lru_cache

import supabase


def get_db_client() -> supabase.Client:
    """
    Create and return a Supabase client.

    Reads connection details in this order:
    1. cfg.database.url and cfg.database.key (from config.yaml via config.py)
    2. SUPABASE_URL and SUPABASE_KEY environment variables (fallback)

    Returns:
        supabase.Client: An authenticated Supabase client ready for queries.

    Raises:
        RuntimeError: If neither config nor environment variables provide the URL/key.
    """
    # Try importing config; fall back to env vars if config isn't loaded yet
    # (e.g., during testing without a config.yaml present).
    try:
        from second_brain.config import cfg
        url = cfg.database.url
        key = cfg.database.key
    except Exception:
        # Fallback: read directly from environment variables
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

    if not url:
        raise RuntimeError(
            "Supabase URL not found. "
            "Set SUPABASE_URL in your environment or database.url_env in config.yaml."
        )
    if not key:
        raise RuntimeError(
            "Supabase key not found. "
            "Set SUPABASE_KEY in your environment or database.key_env in config.yaml."
        )

    return supabase.create_client(url, key)

"""
__main__.py — enables `python -m second_brain` invocation

When Python sees a package with __main__.py, running:
    python -m second_brain sync

is equivalent to:
    second-brain sync

This is useful during development before the package is installed.
"""
from second_brain.cli import app

app()

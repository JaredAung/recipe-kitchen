"""Shared helpers for `.env` loading and API keys."""

from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path) -> None:
    """Load KEY=VALUE lines from `path` into os.environ if the file exists.

    Existing environment variables are not overwritten.
    """
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_api_key(api_key: str | None = None, *, name: str = "GEMINI_API_KEY") -> str:
    """Return `api_key` or the named environment variable.

    Raises RuntimeError if neither is set.
    """
    key = (api_key or os.environ.get(name) or "").strip()
    if not key:
        raise RuntimeError(f"{name} is missing. Set it in .env")
    return key

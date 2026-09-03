"""Track temp videos fetched from storage so they are deleted after the graph."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

logger = logging.getLogger(__name__)

_temp_videos: ContextVar[list[Path] | None] = ContextVar("recipe_temp_videos", default=None)


@contextmanager
def track_temp_videos() -> Iterator[list[Path]]:
    """Record temp video paths and delete them when the block exits."""
    temps: list[Path] = []
    token = _temp_videos.set(temps)
    try:
        yield temps
    finally:
        _temp_videos.reset(token)
        for path in temps:
            path.unlink(missing_ok=True)
            logger.info("Deleted temp video %s", path)


def register_temp_video(path: Path) -> None:
    """Remember `path` for deletion if a graph run is tracking temps."""
    bucket = _temp_videos.get()
    if bucket is not None:
        bucket.append(path)

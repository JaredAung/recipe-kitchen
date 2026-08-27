"""Fetch a subtitle URL and return cue text with timestamps."""

from __future__ import annotations

import re
import urllib.request

_TIMESTAMP = re.compile(
    r"^\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}"
)
_INDEX = re.compile(r"^\d+$")
_TAG = re.compile(r"<[^>]+>")


def _fetch(url: str, *, timeout: float) -> str:
    """GET `url` and return decoded text."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Subtitle download was empty.")
    return data.decode("utf-8-sig")


def _cue_text(raw: str) -> str:
    """Strip SRT/VTT indexes and headers, keeping timestamps and spoken lines."""
    lines: list[str] = []
    for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if upper in {"WEBVTT", "NOTE"} or upper.startswith(("NOTE ", "STYLE", "REGION")):
            continue
        if _INDEX.fullmatch(stripped):
            continue
        if _TIMESTAMP.search(stripped):
            lines.append(stripped)
            continue
        lines.append(_TAG.sub("", stripped))
    return "\n".join(lines).strip()


def download_subtitle_text(subtitles_url: str) -> str:
    """GET `subtitles_url` and return subtitle text with timestamps."""
    text = _cue_text(_fetch(subtitles_url, timeout=30))
    if not text:
        raise RuntimeError("Subtitle file contained no cue text.")
    return text

"""Translate a Burmese transcript into English with Gemini, keeping timestamps."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
PROMPT = (
    "Translate this Burmese recipe transcript into English.\n"
    "Keep every [MM:SS] timestamp on its own line.\n"
    "Do not add titles, notes, or commentary. Output only the translated transcript.\n\n"
)

MYANMAR_RANGES = (
    (0x1000, 0x109F),
    (0xAA60, 0xAA7F),
    (0xA9E0, 0xA9FF),
)


def is_burmese(text: str, *, threshold: float = 0.3) -> bool:
    """Return True if `text` looks Burmese, without calling a model.

    Counts alphabetic characters in Myanmar Unicode blocks and compares
    that share to `threshold`. Timestamps and punctuation are ignored.
    Returns False when there are no letters.
    """
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False
    myanmar = sum(
        any(start <= ord(char) <= end for start, end in MYANMAR_RANGES) for char in letters
    )
    return myanmar / len(letters) > threshold


def _load_env(path: Path) -> None:
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


def _require_api_key(api_key: str | None) -> str:
    """Return `api_key` or GEMINI_API_KEY from the environment.

    Raises RuntimeError if neither is set.
    """
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in .env")
    return key


def translate_to_english(transcript: str, *, api_key: str | None = None) -> str:
    """Translate a timestamped Burmese transcript into English with Gemini.

    If `is_burmese` is False, return `transcript` unchanged and skip Gemini.
    Raises ValueError when the transcript is empty, and RuntimeError when
    the Gemini request fails or returns no text.
    """

    _load_env(ROOT / ".env")
    text = transcript.strip()
    if not text:
        raise ValueError("Transcript is empty.")
    if not is_burmese(text):
        return text

    payload = {
        "contents": [{"parts": [{"text": PROMPT + text}]}],
        "generationConfig": {
            "temperature": 0.2,
        },
    }
    request = urllib.request.Request(
        GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": _require_api_key(api_key),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    translated = "".join(part.get("text", "") for part in parts).strip()
    if not translated:
        raise RuntimeError(f"Gemini returned no text: {body}")
    return translated

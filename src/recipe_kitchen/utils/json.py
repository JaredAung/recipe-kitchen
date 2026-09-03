"""Parse JSON text returned by language models."""

from __future__ import annotations

import json


def parse_json(raw: str) -> dict:
    """Parse JSON, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini returned invalid JSON: {raw}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Gemini returned unexpected JSON: {raw}")
    return parsed

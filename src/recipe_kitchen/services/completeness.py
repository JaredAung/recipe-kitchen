"""Ask Gemini whether extracted ingredients and steps can recreate the dish."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from recipe_kitchen.schemas.extract import Sufficiency
from recipe_kitchen.schemas.recipe import Ingredient, Step

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

PROMPT = """Judge whether a home cook could recreate this dish from the extract alone.

The extract may come from a Facebook caption, video subtitles, or spoken audio.
Treat the steps as a story and the ingredients as the characters.
Set sufficient to true only if:
- The story makes sense and is coherent without any missing gaps.
- The characters are present and have a role in the story.
- The story is complete and does not require any additional information.

Set sufficient to false if a cook would have to guess major ingredients and method.
Do not assume unstated ingredients or steps.
Return JSON only.

Ingredients (JSON):
{ingredients}

Steps (JSON):
{steps}

Source text:
{source_text}
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "sufficient": {"type": "BOOLEAN"},
        "reason": {"type": "STRING"},
    },
    "required": ["sufficient", "reason"],
}


def _load_env(path: Path) -> None:
    """Load KEY=VALUE lines from `path` into os.environ if the file exists."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _require_api_key(api_key: str | None) -> str:
    """Return `api_key` or GEMINI_API_KEY from the environment."""
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in .env")
    return key


def _parse_json(raw: str) -> dict:
    """Parse Gemini JSON, stripping markdown fences if present."""
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


def is_sufficient(
    ingredients: list[Ingredient],
    steps: list[Step],
    *,
    source_text: str = "",
    api_key: str | None = None,
) -> Sufficiency:
    """Return whether a cook could recreate the dish from this extract.

    Skips Gemini when there are no ingredients or no steps.
    """
    if not ingredients or not steps:
        return Sufficiency(
            sufficient=False,
            reason="Need at least one ingredient and one step.",
        )

    _load_env(ROOT / ".env")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": PROMPT.format(
                            ingredients=json.dumps(
                                [item.model_dump() for item in ingredients],
                                ensure_ascii=False,
                            ),
                            steps=json.dumps(
                                [item.model_dump() for item in steps],
                                ensure_ascii=False,
                            ),
                            source_text=source_text.strip() or "(none)",
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
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
    raw = "".join(part.get("text", "") for part in parts).strip()
    if not raw:
        raise RuntimeError(f"Gemini returned no text: {body}")

    parsed = _parse_json(raw)
    return Sufficiency(
        sufficient=bool(parsed.get("sufficient")),
        reason=str(parsed.get("reason") or "").strip(),
    )

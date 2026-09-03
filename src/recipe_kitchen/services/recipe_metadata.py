"""Name the dish and fill listing fields from a sufficient extract."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from recipe_kitchen.schemas.extract import RecipeMetadata
from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.usage import record_gemini_rest
from recipe_kitchen.utils import load_env, parse_json, require_api_key

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

PROMPT = """Fill listing fields for this recipe from the extract.

Return:
- title: a short English dish name a cook would search for
- cuisine: a common kitchen label (Burmese, Chinese, Indian, Thai, or a
  hyphenated fusion name). Empty string if unclear
- description: one or two English sentences a cook would read before starting
- tags: a few short lowercase search labels (protein, method, or dish type)
- total_time_minutes: estimated total minutes to prepare and cook. Omit or
  null if you would have to guess wildly

Do not copy a Facebook caption or marketing line.
Return JSON only.

Ingredients (JSON):
{ingredients}

Steps (JSON):
{steps}
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "cuisine": {"type": "STRING"},
        "description": {"type": "STRING"},
        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "total_time_minutes": {"type": "INTEGER", "nullable": True},
    },
    "required": ["title", "cuisine", "description", "tags"],
}


def _tags(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for item in raw:
        tag = str(item or "").strip()
        key = tag.casefold()
        if not tag or key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def _minutes(raw: object) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None
    try:
        minutes = int(raw)
    except TypeError, ValueError:
        return None
    if minutes < 0:
        return None
    return minutes


def extract_recipe_metadata(
    ingredients: list[Ingredient],
    steps: list[Step],
    *,
    api_key: str | None = None,
) -> RecipeMetadata:
    """Return title, cuisine, description, tags, and estimated total time."""
    load_env(ROOT / ".env")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": PROMPT.format(
                            ingredients=json.dumps(
                                [
                                    item.model_dump(exclude={"amount", "confidence", "evidence"})
                                    for item in ingredients
                                ],
                                ensure_ascii=False,
                            ),
                            steps=json.dumps(
                                [
                                    item.model_dump(exclude={"confidence", "evidence"})
                                    for item in steps
                                ],
                                ensure_ascii=False,
                            ),
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
            "x-goog-api-key": require_api_key(api_key),
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
    record_gemini_rest("gemini_metadata", body, time.perf_counter() - started)

    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = "".join(part.get("text", "") for part in parts).strip()
    if not raw:
        raise RuntimeError(f"Gemini returned no text: {body}")

    parsed = parse_json(raw)
    title = str(parsed.get("title") or "").strip()
    if not title:
        raise RuntimeError(f"Gemini returned no title: {raw}")
    return RecipeMetadata(
        title=title,
        cuisine=str(parsed.get("cuisine") or "").strip(),
        description=str(parsed.get("description") or "").strip(),
        tags=_tags(parsed.get("tags")),
        total_time_minutes=_minutes(parsed.get("total_time_minutes")),
    )

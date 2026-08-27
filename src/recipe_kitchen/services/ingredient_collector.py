"""Extract recipe ingredients from text with Gemini Flash."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, TypedDict

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

IngredientSource = Literal["audio", "caption", "visual"]
SOURCES: tuple[IngredientSource, ...] = ("audio", "caption", "visual")


class Ingredient(TypedDict):
    name: str
    amount: str
    evidence: str
    source: IngredientSource


PROMPT = """Extract cooking ingredients from this recipe text.

The text comes from the {source} channel of a recipe video.

For each ingredient return:
- name: common kitchen name in English
- amount: quantity and unit if stated, otherwise an empty string
- evidence: a short verbatim quote from the text that supports this ingredient

Rules:
- Only list things used as ingredients, not utensils, cookware, or the finished dish.
- Deduplicate the same ingredient. Merge amounts if it is mentioned more than once.
- Keep evidence to one short phrase or sentence copied from the text.
- Do not invent ingredients, amounts, or quotes that are not in the text.
- If the text is Burmese, still return English names; keep evidence in the original language.
- Return JSON only.

Recipe text:
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "ingredients": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "amount": {"type": "STRING"},
                    "evidence": {"type": "STRING"},
                },
                "required": ["name", "amount", "evidence"],
            },
        }
    },
    "required": ["ingredients"],
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


def collect_ingredients(
    text: str,
    source: IngredientSource,
    *,
    api_key: str | None = None,
) -> list[Ingredient]:
    """Extract ingredients from recipe text with Gemini and stamp `source` on each item."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}, got {source!r}")

    _load_env(ROOT / ".env")
    recipe_text = text.strip()
    if not recipe_text:
        raise ValueError("Recipe text is empty.")

    payload = {
        "contents": [{"parts": [{"text": PROMPT.format(source=source) + recipe_text}]}],
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

    extracted = _parse_json(raw).get("ingredients") or []
    ingredients: list[Ingredient] = []
    for item in extracted:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        ingredients.append(
            {
                "name": name,
                "amount": str(item.get("amount") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
                "source": source,
            }
        )
    return ingredients


def main() -> None:
    """Run ingredient extraction on the sample English ElevenLabs transcript."""
    transcript_path = (
        ROOT / "benchmark" / "speech to text" / "transcripts" / "test1_elevenlabs_en.txt"
    )
    print(f"Collecting ingredients from {transcript_path}...")
    transcript = transcript_path.read_text(encoding="utf-8")
    ingredients = collect_ingredients(transcript, source="audio")
    print("\n--- ingredients ---")
    print(json.dumps(ingredients, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

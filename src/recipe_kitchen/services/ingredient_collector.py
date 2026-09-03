"""Extract recipe ingredients from text with Gemini Flash."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, TypedDict

from recipe_kitchen.services.usage import record_gemini_rest
from recipe_kitchen.utils import load_env, parse_json, require_api_key

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


def collect_ingredients(
    text: str,
    source: IngredientSource,
    *,
    api_key: str | None = None,
) -> list[Ingredient]:
    """Extract ingredients from recipe text with Gemini and stamp `source` on each item."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}, got {source!r}")

    load_env(ROOT / ".env")
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
    record_gemini_rest("gemini_ingredients", body, time.perf_counter() - started)

    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = "".join(part.get("text", "") for part in parts).strip()
    if not raw:
        raise RuntimeError(f"Gemini returned no text: {body}")

    extracted = parse_json(raw).get("ingredients") or []
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

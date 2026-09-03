"""Extract ingredients and steps from a recipe video with Gemini vision."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, model_validator

from recipe_kitchen.schemas.recipe import Ingredient, Step, VisualExtract
from recipe_kitchen.utils import load_env, parse_json, require_api_key

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
VIDEO_FPS = 10
REQUEST_TIMEOUT_MS = 300_000

PROMPT = """Watch this cooking video. Extract ingredients and steps from what you can see.

This is the visual channel. Ignore speech.

Priority, in order:
1. On-screen text overlays and packaging labels. If a label is visible, that name
   is the ingredient. Do not add a second name for the same pour based on how the
   food looks. Red dice under a "Capsicum" label is capsicum, not tomato.
2. Packaging (noodle packets, spice jars) when there is no overlay.
3. Cooking actions only when there is no overlay or label for that item
   (eggs cracked, butter in the pan).

For each ingredient return name, amount, and evidence.
For each step return order, instruction, and evidence.

Rules:
- Only list things used as ingredients, not utensils, cookware, watermarks,
  or the finished dish.
- If overlay text exists, evidence must quote that text verbatim.
- Do not invent amounts. If a count is unclear, leave amount empty.
- Deduplicate. Keep steps in order. Split distinct actions.
- Return JSON only.
"""


class _GeminiVisual(BaseModel):
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def stamp_visual_source(cls, data: Any) -> Any:
        """Fill `source="visual"` so Gemini does not have to return it."""
        if not isinstance(data, dict):
            return data
        stamped = dict(data)
        ingredients = []
        for item in stamped.get("ingredients") or []:
            if not isinstance(item, dict):
                ingredients.append(item)
                continue
            name = str(item.get("name") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            if not name or not evidence:
                continue
            ingredients.append({**item, "source": "visual"})
        steps = []
        for index, item in enumerate(stamped.get("steps") or [], start=1):
            if not isinstance(item, dict):
                steps.append(item)
                continue
            if (
                not str(item.get("instruction") or "").strip()
                or not str(item.get("evidence") or "").strip()
            ):
                continue
            steps.append({**item, "source": "visual", "order": item.get("order") or index})
        stamped["ingredients"] = ingredients
        stamped["steps"] = steps
        return stamped


def _parsed_payload(response: types.GenerateContentResponse) -> _GeminiVisual:
    """Return the structured extract."""
    parsed = response.parsed
    if isinstance(parsed, _GeminiVisual):
        return parsed
    if isinstance(parsed, dict):
        return _GeminiVisual.model_validate(parsed)
    raw = (response.text or "").strip()
    if not raw:
        raise RuntimeError("Gemini returned no text.")
    return _GeminiVisual.model_validate(parse_json(raw))


def _usage(response: types.GenerateContentResponse) -> dict[str, int]:
    """Copy token counts from the SDK usage metadata."""
    raw = response.usage_metadata
    if raw is None:
        return {
            "prompt_token_count": 0,
            "candidates_token_count": 0,
            "total_token_count": 0,
        }
    return {
        "prompt_token_count": int(raw.prompt_token_count or 0),
        "candidates_token_count": int(raw.candidates_token_count or 0),
        "total_token_count": int(raw.total_token_count or 0),
    }


def extract_visual_channel(video_path: Path, *, api_key: str | None = None) -> VisualExtract:
    """Send the video to Gemini Flash 3.5 and return visual ingredients and steps."""
    load_env(ROOT / ".env")
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    client = genai.Client(
        api_key=require_api_key(api_key),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
    video_part = types.Part(
        inline_data=types.Blob(data=path.read_bytes(), mime_type="video/mp4"),
        video_metadata=types.VideoMetadata.model_validate({"fps": float(VIDEO_FPS)}),
    )
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[video_part, PROMPT],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=_GeminiVisual,
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
    except errors.APIError as exc:
        raise RuntimeError(f"Gemini HTTP {exc.code}: {exc.message}") from exc

    extracted = _parsed_payload(response)
    ingredients = extracted.ingredients
    steps = [
        step.model_copy(update={"order": max(step.order, 1), "source": "visual"})
        for step in extracted.steps
    ]
    if not ingredients or not steps:
        raise RuntimeError("Gemini visual extract had no ingredients or steps.")

    evidence_text = "\n".join(item.evidence for item in (*ingredients, *steps) if item.evidence)
    return VisualExtract(
        ingredients=ingredients,
        steps=steps,
        transcript_en=evidence_text or "Visual extract from video.",
        usage=_usage(response),
    )

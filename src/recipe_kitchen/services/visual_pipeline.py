"""Extract ingredients and steps from a recipe video with Gemini vision."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, field_validator, model_validator

from recipe_kitchen.schemas.recipe import Ingredient, Step, VisualExtract
from recipe_kitchen.services.audio_extractor import mute_video
from recipe_kitchen.services.usage import record_token_usage
from recipe_kitchen.utils import load_env, parse_json, require_api_key

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
VIDEO_FPS = 2
REQUEST_TIMEOUT_MS = 300_000

PROMPT = """Watch this cooking video. Extract ingredients and steps from what you can see.

This is the visual channel. Ignore speech.

Priority, in order:
1. On-screen text overlays and packaging labels. If a label is visible, that name
   is the ingredient. Do not add a second name for the same pour based on how the
   food looks. Red dice under a "Capsicum" label is capsicum, not tomato.
2. Packaging (noodle packets, spice jars, seasoning sachets) when there is no overlay.
3. Cooking actions when there is no overlay or label for that item
   (eggs cracked, oil poured, butter melted, water added).

For each ingredient return name, amount, evidence, and confidence.
For each step return order, instruction, evidence, and confidence.
Also return an overall confidence for the whole extract.

Rules:
- Only list things used as ingredients, not utensils, cookware, watermarks,
  or the finished dish.
- If overlay text exists, evidence must quote that text verbatim. Overlay text
  is the name. Never copy overlay text into amount.
- Amount only when a number or unit is visible on screen. Otherwise leave
  amount as an empty string.
- Always list anything actually used: oil, butter, water, seasoning packets,
  even when there is no overlay or label.
- Never use generic names like spices, seasoning, or starch. Name each powder
  separately (chili powder, garlic powder, black pepper, cornstarch, flour).
  If several jars or spoons are added, each is its own ingredient. Infer from
  color and container when the label is unreadable, and lower confidence.
- Evidence is a short visual description (red powder from a jar, white coating
  on a plate). Do not use a timestamp alone.
- Confidence is a number from 0 to 1, not a percent:
  - 0.9-1.0 readable overlay, label, or packaging
  - 0.7-0.9 a clear cooking action (egg cracked, oil poured)
  - 0.4-0.6 uncertain identification (unlabeled powder or similar vegetables)
  - below 0.4 only if you must include it; prefer omitting guesses
- Deduplicate. Keep steps in order. Split distinct actions.
- Return JSON only.
"""


class _VisualIngredient(BaseModel):
    name: str
    amount: str = ""
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: object) -> float:
        """Accept 0-1 or a 0-100 percent from Gemini."""
        clamped = _clamp_confidence(value)
        if clamped is None:
            raise ValueError("confidence is required")
        return clamped


class _VisualStep(BaseModel):
    order: int = 1
    instruction: str
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: object) -> float:
        """Accept 0-1 or a 0-100 percent from Gemini."""
        clamped = _clamp_confidence(value)
        if clamped is None:
            raise ValueError("confidence is required")
        return clamped


class _GeminiVisual(BaseModel):
    ingredients: list[_VisualIngredient] = Field(default_factory=list)
    steps: list[_VisualStep] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: object) -> object:
        """Accept 0-1 or a 0-100 percent. Missing overall is filled later."""
        if value is None or value == "":
            return value
        clamped = _clamp_confidence(value)
        return clamped if clamped is not None else value

    @model_validator(mode="before")
    @classmethod
    def drop_overlay_amount_and_fill_confidence(cls, data: Any) -> Any:
        """Clear overlay-copied amounts and default overall confidence."""
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
            amount = str(item.get("amount") or "").strip()
            if amount.casefold() == name.casefold():
                amount = ""
            ingredients.append({**item, "name": name, "amount": amount, "evidence": evidence})
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
            steps.append({**item, "order": item.get("order") or index})
        stamped["ingredients"] = ingredients
        stamped["steps"] = steps
        if stamped.get("confidence") in (None, ""):
            scores = [
                _clamp_confidence(item.get("confidence"))
                for item in (*ingredients, *steps)
                if isinstance(item, dict)
            ]
            nums = [score for score in scores if score is not None]
            if nums:
                stamped["confidence"] = round(sum(nums) / len(nums), 3)
        return stamped


def _clamp_confidence(value: object) -> float | None:
    """Return a 0-1 score, treating values above 1 as percents."""
    if value is None or value == "":
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        score = float(value)
    except ValueError:
        return None
    if score > 1:
        score = min(score, 100.0) / 100.0 if score >= 2 else 1.0
    return max(0.0, round(score, 3))


def _to_ingredients(items: list[_VisualIngredient]) -> list[Ingredient]:
    return [
        Ingredient(
            name=item.name,
            amount=item.amount,
            evidence=item.evidence,
            source="visual",
            confidence=item.confidence,
        )
        for item in items
    ]


def _to_steps(items: list[_VisualStep]) -> list[Step]:
    return [
        Step(
            order=max(item.order, 1),
            instruction=item.instruction,
            evidence=item.evidence,
            source="visual",
            confidence=item.confidence,
        )
        for item in items
    ]


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
    """Send the muted video to Gemini Flash 3.5 and return visual ingredients and steps.

    Audio is stripped first so this channel is sight-only.
    """
    load_env(ROOT / ".env")
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    client = genai.Client(
        api_key=require_api_key(api_key),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
    video_part = types.Part(
        inline_data=types.Blob(data=mute_video(path), mime_type="video/mp4"),
        video_metadata=types.VideoMetadata.model_validate({"fps": float(VIDEO_FPS)}),
    )
    try:
        started = time.perf_counter()
        response = client.models.generate_content(
            model=MODEL,
            contents=[video_part, PROMPT],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=_GeminiVisual,
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        record_token_usage(
            "gemini_visual",
            time.perf_counter() - started,
            _usage(response),
        )
    except errors.APIError as exc:
        raise RuntimeError(f"Gemini HTTP {exc.code}: {exc.message}") from exc

    extracted = _parsed_payload(response)
    ingredients = _to_ingredients(extracted.ingredients)
    steps = _to_steps(extracted.steps)
    if not ingredients or not steps:
        raise RuntimeError("Gemini visual extract had no ingredients or steps.")

    evidence_text = "\n".join(item.evidence for item in (*ingredients, *steps) if item.evidence)
    return VisualExtract(
        ingredients=ingredients,
        steps=steps,
        transcript_en=evidence_text or "Visual extract from video.",
        confidence=extracted.confidence,
        usage=_usage(response),
    )

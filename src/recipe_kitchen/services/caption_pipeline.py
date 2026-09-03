"""Extract ingredients and steps from recipe text."""

from __future__ import annotations

import logging
import re

from recipe_kitchen.schemas.extract import CaptionExtract
from recipe_kitchen.schemas.recipe import CollectorSource, Ingredient, Step
from recipe_kitchen.services.ingredient_collector import collect_ingredients
from recipe_kitchen.services.steps_collector import collect_steps
from recipe_kitchen.services.translater import is_burmese, translate_to_english

logger = logging.getLogger(__name__)

_QUANTITY = re.compile(
    r"(?:\d+\s*/\s*\d+|\d+(?:\.\d+)?|[¼½¾⅓⅔])\s*"
    r"(?:tsp|tbsp|teaspoons?|tablespoons?|cups?|cloves?|grams?|"
    r"kg|oz|lbs?|ml|liters?|litres?|inches?|in|ticals?)\b",
    re.IGNORECASE,
)
_NUMBERED_STEP = re.compile(r"(?:^|[\s;])\d+[\.\)]\s+[A-Za-z]")
_BULLET_LINE = re.compile(r"(?:^|\n)\s*[-*•]\s+\S")
_METHOD_VERB = re.compile(
    r"\b(?:add|mix|whisk|fry|saute|sauté|simmer|boil|bake|season|"
    r"marinate|stir[- ]fry|stir|pour|heat|slice|chop|drain|coat|"
    r"brown|reduce|grate|dissolve)\b",
    re.IGNORECASE,
)


def looks_like_recipe(text: str) -> bool:
    """True when `text` looks like a method, not a title or marketing line.

    Accepts a quantity with unit, a numbered step, three bullet lines, or two
    cooking-method sentences. Dish names, hashtags, and “here is a recipe”
    posts return False.
    """
    raw = text.strip()
    if not raw:
        return False
    if _QUANTITY.search(raw) or _NUMBERED_STEP.search(raw):
        return True
    if len(_BULLET_LINE.findall(raw)) >= 3:
        return True
    method_sentences = [
        part for part in re.split(r"[.!?\n]+", raw) if part.strip() and _METHOD_VERB.search(part)
    ]
    return len(method_sentences) >= 2


def english_caption_text(extracted: CaptionExtract) -> str:
    """Return English text for a caption extract, translating only if needed."""
    if extracted.text_en:
        return extracted.text_en
    if extracted.text_my:
        return translate_to_english(extracted.text_my)
    return extracted.source_text


def _text_extract(*, raw: str, ingredients: list[Ingredient], steps: list[Step]) -> CaptionExtract:
    """Stamp language fields without calling Gemini."""
    if is_burmese(raw):
        return CaptionExtract(
            ingredients=ingredients,
            steps=steps,
            source_text=raw,
            text_my=raw,
        )
    return CaptionExtract(
        ingredients=ingredients,
        steps=steps,
        source_text=raw,
        text_en=raw,
    )


def extract_caption_channel(text: str, *, source: CollectorSource) -> CaptionExtract:
    """Collect ingredients and steps from `text` and stamp them with `source`.

    Empty text or a non-recipe caption returns an empty extract and does not
    call Gemini. Collects from the original language so evidence stays verbatim.
    Translation is deferred until `english_caption_text`.
    """
    raw = text.strip()
    if not raw:
        return CaptionExtract(ingredients=[], steps=[], source_text="")
    if not looks_like_recipe(raw):
        logger.info("Skipping Gemini extract; caption is not a recipe (%s chars)", len(raw))
        return _text_extract(raw=raw, ingredients=[], steps=[])

    ingredients = [
        Ingredient.model_validate(item) for item in collect_ingredients(raw, source=source)
    ]
    steps = [Step.model_validate(item) for item in collect_steps(raw, source=source)]
    return _text_extract(raw=raw, ingredients=ingredients, steps=steps)

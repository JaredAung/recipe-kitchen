"""Extract ingredients and steps from recipe text."""

from __future__ import annotations

from recipe_kitchen.schemas.extract import CaptionExtract
from recipe_kitchen.schemas.recipe import CollectorSource, Ingredient, Step
from recipe_kitchen.services.ingredient_collector import collect_ingredients
from recipe_kitchen.services.steps_collector import collect_steps
from recipe_kitchen.services.translater import is_burmese, translate_to_english


def english_caption_text(extracted: CaptionExtract) -> str:
    """Return English text for a caption extract, translating only if needed."""
    if extracted.text_en:
        return extracted.text_en
    if extracted.text_my:
        return translate_to_english(extracted.text_my)
    return extracted.source_text


def extract_caption_channel(text: str, *, source: CollectorSource) -> CaptionExtract:
    """Collect ingredients and steps from `text` and stamp them with `source`.

    Empty text returns an empty extract and does not call Gemini.
    Collects from the original language so evidence stays verbatim.
    Translation is deferred until `english_caption_text`.
    """
    raw = text.strip()
    if not raw:
        return CaptionExtract(ingredients=[], steps=[], source_text="")

    ingredients = [
        Ingredient.model_validate(item) for item in collect_ingredients(raw, source=source)
    ]
    steps = [Step.model_validate(item) for item in collect_steps(raw, source=source)]
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

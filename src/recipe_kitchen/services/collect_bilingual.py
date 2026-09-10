"""Collect ingredients and steps from Burmese and English text in parallel."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from recipe_kitchen.schemas.recipe import CollectorSource, Ingredient, Step
from recipe_kitchen.services.ingredient_collector import collect_ingredients
from recipe_kitchen.services.reconcile_channel import reconcile_ingredients, reconcile_steps
from recipe_kitchen.services.steps_collector import collect_steps


def collect_bilingual(
    text_my: str,
    text_en: str,
    *,
    source: CollectorSource,
) -> tuple[list[Ingredient], list[Step]]:
    """Extract from both languages, then keep one row per mention."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        ingredients_my = pool.submit(_ingredients, text_my, source)
        steps_my = pool.submit(_steps, text_my, source)
        ingredients_en = pool.submit(_ingredients, text_en, source)
        steps_en = pool.submit(_steps, text_en, source)
        from_my_ingredients = ingredients_my.result()
        from_my_steps = steps_my.result()
        from_en_ingredients = ingredients_en.result()
        from_en_steps = steps_en.result()
    return (
        reconcile_ingredients(from_my_ingredients, from_en_ingredients),
        reconcile_steps(from_my_steps, from_en_steps),
    )


def _ingredients(text: str, source: CollectorSource) -> list[Ingredient]:
    return [Ingredient.model_validate(item) for item in collect_ingredients(text, source=source)]


def _steps(text: str, source: CollectorSource) -> list[Step]:
    return [Step.model_validate(item) for item in collect_steps(text, source=source)]

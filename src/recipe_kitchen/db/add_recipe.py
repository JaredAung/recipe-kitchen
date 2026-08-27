"""Insert a recipe and its extracted ingredients and steps."""

from __future__ import annotations

from typing import Any

from supabase import Client

from recipe_kitchen.db.supabase import get_supabase_admin
from recipe_kitchen.schemas.recipe import RecipeCreate

SOURCES = ("audio", "caption", "visual")


def _execute(result: Any, action: str) -> list[dict[str, Any]]:
    """Return insert/select rows from a Supabase response, or raise on failure."""
    error = getattr(result, "error", None)
    if error:
        raise RuntimeError(f"Failed to {action}: {error}")
    data = result.data or []
    if not data:
        raise RuntimeError(f"Failed to {action}: empty response")
    return data


def _channel_status(recipe: RecipeCreate) -> dict[str, str]:
    """Mark audio/caption/visual as ready when that channel contributed data."""
    status = {source: "idle" for source in SOURCES}
    found: set[str] = set()
    if recipe.transcript_my or recipe.transcript_en:
        found.add("audio")
    if recipe.caption_text:
        found.add("caption")
    for item in (*recipe.ingredients, *recipe.steps):
        found.add(item.source)
    for source in found:
        status[source] = "ready"
    return status


def add_recipe(
    recipe: RecipeCreate | dict[str, Any],
    *,
    client: Client | None = None,
) -> dict[str, Any]:
    """Validate `recipe`, insert it with ingredients and steps, and return the saved row.

    Uses the admin client unless `client` is passed. Deletes the recipe if
    child-row inserts fail.
    """
    data = recipe if isinstance(recipe, RecipeCreate) else RecipeCreate.model_validate(recipe)
    db = client or get_supabase_admin()

    recipe_payload = data.model_dump(
        mode="json",
        exclude={"ingredients", "steps"},
        exclude_none=True,
    )
    recipe_payload["channel_status"] = _channel_status(data)
    if not data.transcript_my:
        recipe_payload.pop("transcript_my", None)
    if not data.caption_text:
        recipe_payload.pop("caption_text", None)

    inserted = _execute(
        db.table("recipes").insert(recipe_payload).execute(),
        "insert recipe",
    )
    saved = inserted[0]
    recipe_id = saved["id"]

    try:
        saved_ingredients: list[dict[str, Any]] = []
        if data.ingredients:
            saved_ingredients = _execute(
                db.table("recipe_ingredients")
                .insert(
                    [
                        {
                            "recipe_id": recipe_id,
                            "name": item.name,
                            "amount": item.amount,
                            "evidence": item.evidence,
                            "source": item.source,
                            "sort_order": index,
                        }
                        for index, item in enumerate(data.ingredients)
                    ]
                )
                .execute(),
                "insert recipe ingredients",
            )

        saved_steps: list[dict[str, Any]] = []
        if data.steps:
            saved_steps = _execute(
                db.table("recipe_steps")
                .insert(
                    [
                        {
                            "recipe_id": recipe_id,
                            "step_order": item.order,
                            "instruction": item.instruction,
                            "evidence": item.evidence,
                            "source": item.source,
                        }
                        for item in data.steps
                    ]
                )
                .execute(),
                "insert recipe steps",
            )
    except Exception:
        db.table("recipes").delete().eq("id", recipe_id).execute()
        raise

    return {
        **saved,
        "ingredients": saved_ingredients,
        "steps": saved_steps,
    }

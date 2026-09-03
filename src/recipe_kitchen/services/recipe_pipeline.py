"""Caption → subtitles → audio → visual, stopping when the extract can recreate the dish."""

from __future__ import annotations

import logging
from pathlib import Path

from recipe_kitchen.db.add_recipe import add_recipe
from recipe_kitchen.graph.graph import recipe_graph
from recipe_kitchen.graph.temp_video import track_temp_videos
from recipe_kitchen.schemas.extract import (
    CaptionExtract,
    RecipeGraphState,
    RecipePipelineResult,
    StoppedAfter,
    Sufficiency,
)
from recipe_kitchen.schemas.recipe import Ingredient, RecipeCreate, Step
from recipe_kitchen.services.caption_pipeline import english_caption_text

ROOT = Path(__file__).resolve().parents[3]
TEST1_VIDEO = ROOT / "testing-material" / "test1.mp4"
TEST1_CAPTION = "👉Spicy fried fish that will make even relatives forget👍😋"

logger = logging.getLogger(__name__)


def _finish(
    *,
    stopped_after: StoppedAfter,
    judgment: Sufficiency,
    ingredients: list[Ingredient],
    steps: list[Step],
    transcript_my: str | None,
    transcript_en: str,
    caption_text: str,
    subtitle_text: str,
    original_filename: str | None,
    source_url: str | None,
    video_path: str | None,
    thumbnail_path: str | None,
    save: bool,
) -> RecipePipelineResult:
    """Build the result and optionally persist it."""
    if save:
        saved = add_recipe(
            RecipeCreate(
                transcript_my=transcript_my,
                transcript_en=transcript_en,
                ingredients=ingredients,
                steps=steps,
                original_filename=original_filename,
                source_url=source_url,
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                caption_text=caption_text,
                extraction_meta={
                    "stopped_after": stopped_after,
                    "sufficient": judgment.sufficient,
                    "reason": judgment.reason,
                    "subtitle_text": subtitle_text,
                },
            )
        )
        recipe_id = str(saved["id"])
        logger.info("Saved recipe %s", recipe_id)
    else:
        recipe_id = ""
    return RecipePipelineResult(
        id=recipe_id,
        stopped_after=stopped_after,
        sufficient=judgment.sufficient,
        reason=judgment.reason,
        transcript_my=transcript_my,
        transcript_en=transcript_en,
        ingredients=ingredients,
        steps=steps,
        caption_text=caption_text,
    )


def _as_state(raw: object) -> RecipeGraphState:
    """Normalize a graph invoke result to `RecipeGraphState`."""
    if isinstance(raw, RecipeGraphState):
        return raw
    if isinstance(raw, dict):
        return RecipeGraphState.model_validate(raw)
    raise TypeError(f"Unexpected graph result: {type(raw)!r}")


def run_recipe_pipeline(
    *,
    caption: str = "",
    subtitle_text: str = "",
    video_path: Path | None = None,
    original_filename: str | None = None,
    source_url: str | None = None,
    video_storage_path: str | None = None,
    thumbnail_path: str | None = None,
    save: bool = True,
) -> RecipePipelineResult:
    """Extract from caption, then subtitles, then audio, then visual.

    Stops as soon as `is_sufficient` is true. Later channels run only when
    earlier ones are not enough and their input is present.
    """
    logger.info(
        "Recipe graph start caption=%s subtitle=%s local_video=%s stored_video=%s",
        bool(caption.strip()),
        bool(subtitle_text.strip()),
        str(video_path) if video_path else None,
        (video_storage_path or "").strip() or None,
    )
    with track_temp_videos():
        state = _as_state(
            recipe_graph.invoke(
                RecipeGraphState(
                    caption=caption.strip(),
                    subtitle_text=subtitle_text.strip(),
                    video_path=str(video_path) if video_path else None,
                    video_storage_path=(video_storage_path or "").strip() or None,
                )
            )
        )
    if state.phase is None:
        raise RuntimeError("Recipe graph finished without running a channel.")
    logger.info(
        "Recipe graph done stopped_after=%s sufficient=%s ingredients=%s steps=%s",
        state.phase,
        state.sufficient,
        len(state.ingredients),
        len(state.steps),
    )

    transcript_en = state.transcript_en
    if state.phase in {"caption", "subtitle"}:
        transcript_en = english_caption_text(
            CaptionExtract(
                ingredients=state.ingredients,
                steps=state.steps,
                source_text=state.caption or state.subtitle_text,
                text_my=state.text_my,
                text_en=state.text_en,
            )
        )
    elif not transcript_en.strip():
        transcript_en = state.visual_text or "Recipe extract."

    return _finish(
        stopped_after=state.phase,
        judgment=Sufficiency(sufficient=state.sufficient, reason=state.reason),
        ingredients=state.ingredients,
        steps=state.steps,
        transcript_my=state.transcript_my,
        transcript_en=transcript_en,
        caption_text=state.caption,
        subtitle_text=state.subtitle_text,
        original_filename=original_filename,
        source_url=source_url,
        video_path=video_storage_path,
        thumbnail_path=thumbnail_path,
        save=save,
    )


def main() -> None:
    """Run the recipe graph on testing-material/test1.mp4 and print the extract."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not TEST1_VIDEO.is_file():
        raise FileNotFoundError(f"Video not found: {TEST1_VIDEO}")
    print(f"Running recipe pipeline on {TEST1_VIDEO}...")
    result = run_recipe_pipeline(
        caption=TEST1_CAPTION,
        video_path=TEST1_VIDEO,
        original_filename=TEST1_VIDEO.name,
        save=False,
    )
    print(f"stopped_after: {result.stopped_after}")
    print(f"sufficient: {result.sufficient}")
    print(f"reason: {result.reason}")
    print("--- ingredients ---")
    for item in result.ingredients:
        print(f"  [{item.source}] {item.name} {item.amount!r} | {item.evidence}")
    print("--- steps ---")
    for step in result.steps:
        print(f"  [{step.source}] {step.order}. {step.instruction} | {step.evidence}")


if __name__ == "__main__":
    main()

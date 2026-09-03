"""Caption → subtitles → audio → visual, stopping when the extract can recreate the dish."""

from __future__ import annotations

import logging
from pathlib import Path

from recipe_kitchen.graph.graph import recipe_graph
from recipe_kitchen.graph.nodes import english_transcript
from recipe_kitchen.graph.temp_video import track_temp_videos
from recipe_kitchen.schemas.extract import RecipeGraphState, RecipePipelineResult
from recipe_kitchen.services.ingestion.video_to_bucket import delete_video

ROOT = Path(__file__).resolve().parents[3]
TEST1_VIDEO = ROOT / "testing-material" / "test1.mp4"
TEST1_CAPTION = "👉Spicy fried fish that will make even relatives forget👍😋"

logger = logging.getLogger(__name__)


def _as_state(raw: object) -> RecipeGraphState:
    """Normalize a graph invoke result to `RecipeGraphState`."""
    if isinstance(raw, RecipeGraphState):
        return raw
    if isinstance(raw, dict):
        return RecipeGraphState.model_validate(raw)
    raise TypeError(f"Unexpected graph result: {type(raw)!r}")


def _to_result(state: RecipeGraphState) -> RecipePipelineResult:
    """Copy graph state into the API result. `id` is set only after a save."""
    if state.phase is None:
        raise RuntimeError("Recipe graph finished without running a channel.")
    transcript_en = state.transcript_en
    if not transcript_en.strip():
        transcript_en = english_transcript(state)
    return RecipePipelineResult(
        id=state.recipe_id,
        stopped_after=state.phase,
        sufficient=state.sufficient,
        reason=state.reason,
        title=state.title,
        cuisine=state.cuisine,
        description=state.description,
        tags=state.tags,
        total_time_minutes=state.total_time_minutes,
        validation_issues=state.validation_issues,
        validation_confidence=state.validation_confidence,
        transcript_my=state.transcript_my,
        transcript_en=transcript_en,
        ingredients=state.ingredients,
        steps=state.steps,
        caption_text=state.caption,
    )


def _delete_stored_video(object_path: str | None) -> None:
    """Remove a pipeline video from Storage. Logs and continues on failure."""
    path = (object_path or "").strip()
    if not path:
        return
    try:
        delete_video(path)
        logger.info("Deleted stored video %s", path)
    except RuntimeError:
        logger.exception("Failed to delete stored video %s", path)


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

    Stops as soon as `is_sufficient` is true, then names the dish, flags
    grounding issues, and saves when `save` is true. Later channels run only
    when earlier ones are not enough and their input is present.

    After the graph finishes or fails, deletes `video_storage_path` from the
    bucket. Local uploads (`video_path`) and thumbnails are left in place.
    """
    stored_video = (video_storage_path or "").strip() or None
    logger.info(
        "Recipe graph start caption=%s subtitle=%s local_video=%s stored_video=%s",
        bool(caption.strip()),
        bool(subtitle_text.strip()),
        str(video_path) if video_path else None,
        stored_video,
    )
    try:
        with track_temp_videos():
            state = _as_state(
                recipe_graph.invoke(
                    RecipeGraphState(
                        caption=caption.strip(),
                        subtitle_text=subtitle_text.strip(),
                        video_path=str(video_path) if video_path else None,
                        video_storage_path=stored_video,
                        save=save,
                        original_filename=original_filename,
                        source_url=source_url,
                        thumbnail_path=thumbnail_path,
                    )
                )
            )
        logger.info(
            "Recipe graph done stopped_after=%s sufficient=%s title=%r "
            "id=%s ingredients=%s steps=%s",
            state.phase,
            state.sufficient,
            state.title,
            state.recipe_id,
            len(state.ingredients),
            len(state.steps),
        )
        return _to_result(state)
    finally:
        _delete_stored_video(stored_video)


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
    print(f"title: {result.title}")
    print(f"cuisine: {result.cuisine}")
    print(f"description: {result.description}")
    print(f"tags: {result.tags}")
    print(f"total_time_minutes: {result.total_time_minutes}")
    print(f"validation_confidence: {result.validation_confidence}")
    print(f"reason: {result.reason}")
    print("--- ingredients ---")
    for item in result.ingredients:
        print(f"  [{item.source}] {item.name} {item.amount!r} | {item.evidence}")
    print("--- steps ---")
    for step in result.steps:
        print(f"  [{step.source}] {step.order}. {step.instruction} | {step.evidence}")


if __name__ == "__main__":
    main()

from unittest.mock import MagicMock, patch

from recipe_kitchen.schemas.extract import RecipePipelineResult
from recipe_kitchen.schemas.jobs import Job
from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.worker import handle_job, process_message


def _recipe_result() -> RecipePipelineResult:
    return RecipePipelineResult(
        id="abc",
        stopped_after="caption",
        sufficient=True,
        reason="complete",
        transcript_en="Fry a whole fish",
        ingredients=[Ingredient(name="fish", amount="1", evidence="whole fish", source="caption")],
        steps=[Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")],
        caption_text="Fry a whole fish",
    )


def test_process_message_skips_missing_job() -> None:
    with (
        patch("recipe_kitchen.worker.claim_job", return_value=None),
        patch("recipe_kitchen.worker.handle_job") as handle,
    ):
        process_message("job-1")
    handle.assert_not_called()


def test_handle_recipe_calls_pipeline() -> None:
    job = Job(
        id="job-1",
        kind="recipe",
        status="running",
        input={
            "caption": "Fry a whole fish",
            "subtitle_text": "",
            "video": "123/video.mp4",
            "thumbnail": "123/thumbnail.jpg",
            "source_url": "https://www.facebook.com/reel/123",
            "original_filename": None,
        },
    )
    result = _recipe_result()
    with (
        patch("recipe_kitchen.worker.run_recipe_pipeline", return_value=result) as run_pipeline,
        patch("recipe_kitchen.worker.finish_job") as finish,
    ):
        handle_job(job)

    kwargs = run_pipeline.call_args.kwargs
    assert kwargs["caption"] == "Fry a whole fish"
    assert kwargs["video_storage_path"] == "123/video.mp4"
    assert kwargs["thumbnail_path"] == "123/thumbnail.jpg"
    assert kwargs["original_filename"] == "video.mp4"
    assert kwargs["save"] is True
    finish.assert_called_once()
    assert finish.call_args.args[0] == "job-1"
    assert finish.call_args.args[1]["id"] == "abc"


def test_process_message_marks_pipeline_failed() -> None:
    job = Job(id="job-1", kind="recipe", status="running", input={"caption": "x"})
    with (
        patch("recipe_kitchen.worker.claim_job", return_value=job),
        patch("recipe_kitchen.worker.handle_job", side_effect=RuntimeError("Gemini failed")),
        patch("recipe_kitchen.worker.fail_job") as fail,
    ):
        process_message("job-1")
    fail.assert_called_once_with("job-1", "pipeline_failed")


def test_handle_ingest_calls_facebook_ingest() -> None:
    job = Job(
        id="job-2",
        kind="ingest",
        status="running",
        input={"url": "https://www.facebook.com/reel/123"},
    )
    ingest = MagicMock()
    ingest.model_dump.return_value = {"video": "123/video.mp4"}
    with (
        patch("recipe_kitchen.worker.run_facebook_ingest", return_value=ingest) as run_ingest,
        patch("recipe_kitchen.worker.finish_job") as finish,
    ):
        handle_job(job)
    run_ingest.assert_called_once_with("https://www.facebook.com/reel/123")
    finish.assert_called_once_with("job-2", {"video": "123/video.mp4"})

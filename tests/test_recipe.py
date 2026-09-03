from unittest.mock import patch

from fastapi.testclient import TestClient

from recipe_kitchen.schemas.extract import RecipePipelineResult
from recipe_kitchen.schemas.recipe import Ingredient, Step

RUN_PIPELINE = "recipe_kitchen.api.routes.recipe.run_recipe_pipeline"

FISH = Ingredient(name="fish", amount="1", evidence="whole fish", source="caption")
FRY = Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")


def _result() -> RecipePipelineResult:
    return RecipePipelineResult(
        id="abc",
        stopped_after="caption",
        sufficient=True,
        reason="complete",
        transcript_en="Fry a whole fish",
        ingredients=[FISH],
        steps=[FRY],
        caption_text="Fry a whole fish",
    )


def test_recipe_rejects_empty_body(client: TestClient) -> None:
    response = client.post("/recipe", json={})
    assert response.status_code == 400
    assert "caption" in response.json()["detail"]


def test_recipe_extracts_from_caption_without_video(client: TestClient) -> None:
    with patch(RUN_PIPELINE, return_value=_result()) as run_pipeline:
        response = client.post("/recipe", json={"caption": "Fry a whole fish"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "abc"
    assert body["stopped_after"] == "caption"
    kwargs = run_pipeline.call_args.kwargs
    assert kwargs["caption"] == "Fry a whole fish"
    assert kwargs.get("video_path") is None
    assert kwargs["video_storage_path"] is None
    assert kwargs["save"] is True


def test_recipe_passes_storage_path_without_download(client: TestClient) -> None:
    with patch(RUN_PIPELINE, return_value=_result()) as run_pipeline:
        response = client.post(
            "/recipe",
            json={
                "caption": "Maggi Omlette",
                "subtitle_text": "add salt",
                "video": "123/video.mp4",
                "thumbnail": "123/thumbnail.jpg",
                "source_url": "https://www.facebook.com/reel/123",
            },
        )

    assert response.status_code == 200
    kwargs = run_pipeline.call_args.kwargs
    assert kwargs["caption"] == "Maggi Omlette"
    assert kwargs["subtitle_text"] == "add salt"
    assert kwargs.get("video_path") is None
    assert kwargs["video_storage_path"] == "123/video.mp4"
    assert kwargs["thumbnail_path"] == "123/thumbnail.jpg"
    assert kwargs["original_filename"] == "video.mp4"
    assert kwargs["save"] is True


def test_recipe_returns_502_when_pipeline_fails(client: TestClient) -> None:
    with patch(RUN_PIPELINE, side_effect=RuntimeError("Gemini failed")):
        response = client.post("/recipe", json={"caption": "thin caption"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Gemini failed"

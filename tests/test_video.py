from unittest.mock import patch

from fastapi.testclient import TestClient

from recipe_kitchen.schemas.recipe import Ingredient, Step, VisualExtract

EXTRACT_VISUAL = "recipe_kitchen.api.routes.video.extract_visual_channel"
ADD_RECIPE = "recipe_kitchen.api.routes.video.add_recipe"


def test_video_rejects_unsupported_type(client: TestClient) -> None:
    response = client.post(
        "/video",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_video_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/video",
        files={"file": ("video.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."


def test_video_saves_visual_extract(client: TestClient) -> None:
    extracted = VisualExtract(
        ingredients=[
            Ingredient(name="capsicum", amount="", evidence="Capsicum", source="visual"),
        ],
        steps=[
            Step(order=1, instruction="Add capsicum", evidence="Capsicum", source="visual"),
        ],
        transcript_en="Capsicum",
        usage={"total_token_count": 1},
    )
    with (
        patch(EXTRACT_VISUAL, return_value=extracted) as extract_visual,
        patch(ADD_RECIPE, return_value={"id": "abc"}) as save_recipe,
    ):
        response = client.post(
            "/video",
            files={"file": ("test6.mp4", b"fake", "video/mp4")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "abc"
    assert body["ingredients"][0]["source"] == "visual"
    assert body["usage"]["total_token_count"] == 1
    extract_visual.assert_called_once()
    save_recipe.assert_called_once()

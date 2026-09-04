from unittest.mock import patch

from fastapi.testclient import TestClient

ENQUEUE = "recipe_kitchen.api.routes.recipe.enqueue_job"


def test_recipe_rejects_empty_body(client: TestClient) -> None:
    response = client.post("/recipe", json={})
    assert response.status_code == 400
    assert "caption" in response.json()["detail"]


def test_recipe_enqueues_caption_without_video(client: TestClient) -> None:
    with patch(ENQUEUE, return_value="job-1") as enqueue:
        response = client.post("/recipe", json={"caption": "Fry a whole fish"})

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-1"}
    enqueue.assert_called_once()
    kind, payload = enqueue.call_args.args
    assert kind == "recipe"
    assert payload["caption"] == "Fry a whole fish"
    assert payload["video"] == ""
    assert payload["subtitle_text"] == ""


def test_recipe_enqueues_storage_path(client: TestClient) -> None:
    with patch(ENQUEUE, return_value="job-2") as enqueue:
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

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-2"}
    payload = enqueue.call_args.args[1]
    assert payload["caption"] == "Maggi Omlette"
    assert payload["subtitle_text"] == "add salt"
    assert payload["video"] == "123/video.mp4"
    assert payload["thumbnail"] == "123/thumbnail.jpg"
    assert payload["source_url"] == "https://www.facebook.com/reel/123"


def test_recipe_returns_502_when_enqueue_fails(client: TestClient) -> None:
    with patch(ENQUEUE, side_effect=RuntimeError("Failed to enqueue job")):
        response = client.post("/recipe", json={"caption": "thin caption"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to enqueue job"

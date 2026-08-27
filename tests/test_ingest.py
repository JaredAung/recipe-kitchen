from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tests.facebook_scrape import SCRAPE


def test_ingest_rejects_non_facebook_url(client: TestClient) -> None:
    response = client.post("/ingest", json={"url": "https://example.com/video"})
    assert response.status_code == 422


def test_ingest_rejects_facebook_profile_url(client: TestClient) -> None:
    response = client.post("/ingest", json={"url": "https://www.facebook.com/someone"})
    assert response.status_code == 422


def test_ingest_returns_502_when_scrape_fails(client: TestClient) -> None:
    with patch(
        "recipe_kitchen.api.routes.ingest.fetch_facebook",
        side_effect=RuntimeError("APIFY_API_TOKEN is missing. Set it in .env"),
    ):
        response = client.post(
            "/ingest",
            json={"url": "https://www.facebook.com/reel/123"},
        )
    assert response.status_code == 502


def test_ingest_stores_video_thumbnail_and_subtitles(client: TestClient) -> None:
    video = MagicMock(path="123/video.mp4")
    thumbnail = MagicMock(path="123/thumbnail.jpg")
    with (
        patch(
            "recipe_kitchen.api.routes.ingest.fetch_facebook",
            return_value=[SCRAPE],
        ),
        patch(
            "recipe_kitchen.api.routes.ingest.download_video",
            return_value=video,
        ) as download_video,
        patch(
            "recipe_kitchen.api.routes.ingest.download_thumbnail",
            return_value=thumbnail,
        ),
        patch(
            "recipe_kitchen.api.routes.ingest.download_subtitle_text",
            return_value="hello",
        ),
    ):
        response = client.post(
            "/ingest",
            json={"url": "https://www.facebook.com/reel/123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["video"] == "123/video.mp4"
    assert body["thumbnail"] == "123/thumbnail.jpg"
    assert body["subtitle_text"] == "hello"
    assert body["media"]["video_id"] == "123"
    download_video.assert_called_once()

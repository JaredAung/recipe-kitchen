from unittest.mock import MagicMock, patch

import pytest

from recipe_kitchen.services.ingestion.facebook_ingest import run_facebook_ingest
from tests.facebook_scrape import SCRAPE


def test_run_facebook_ingest_raises_when_scrape_fails() -> None:
    with (
        patch(
            "recipe_kitchen.services.ingestion.facebook_ingest.fetch_facebook",
            side_effect=RuntimeError("APIFY_API_TOKEN is missing. Set it in .env"),
        ),
        pytest.raises(RuntimeError, match="APIFY_API_TOKEN"),
    ):
        run_facebook_ingest("https://www.facebook.com/reel/123")


def test_run_facebook_ingest_stores_video_thumbnail_and_subtitles() -> None:
    video = MagicMock(path="123/video.mp4")
    thumbnail = MagicMock(path="123/thumbnail.jpg")
    with (
        patch(
            "recipe_kitchen.services.ingestion.facebook_ingest.fetch_facebook",
            return_value=[SCRAPE],
        ),
        patch(
            "recipe_kitchen.services.ingestion.facebook_ingest.download_video",
            return_value=video,
        ) as download_video,
        patch(
            "recipe_kitchen.services.ingestion.facebook_ingest.download_thumbnail",
            return_value=thumbnail,
        ),
        patch(
            "recipe_kitchen.services.ingestion.facebook_ingest.download_subtitle_text",
            return_value="hello",
        ),
    ):
        result = run_facebook_ingest("https://www.facebook.com/reel/123")

    assert result.video == "123/video.mp4"
    assert result.thumbnail == "123/thumbnail.jpg"
    assert result.subtitle_text == "hello"
    assert result.media.video_id == "123"
    download_video.assert_called_once()

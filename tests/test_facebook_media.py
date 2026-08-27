from recipe_kitchen.schemas.facebook import FacebookMedia
from recipe_kitchen.services.ingestion.cleaner import extract_facebook_media
from tests.facebook_scrape import SCRAPE


def test_extract_facebook_media_reads_nested_fields() -> None:
    media = extract_facebook_media([SCRAPE])
    assert media.video_id == "123"
    assert media.caption == "A recipe"
    assert media.hd_url == "https://cdn.example/hd.mp4"
    assert media.sd_url == "https://cdn.example/sd.mp4"
    assert media.duration == 12.5
    assert media.width == 1080
    assert media.height == 1920
    assert media.audio_available == "AVAILABLE"
    assert media.creator_name == "Chef"


def test_facebook_media_coerces_blank_and_invalid_values() -> None:
    media = FacebookMedia.model_validate(
        {
            "video_id": "  ",
            "duration": "nope",
            "width": True,
            "audio_available": "",
        }
    )
    assert media.video_id == ""
    assert media.duration == 0.0
    assert media.width == 0
    assert media.audio_available == "Not available"

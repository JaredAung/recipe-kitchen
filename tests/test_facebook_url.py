import pytest

from recipe_kitchen.schemas.facebook import parse_facebook_video_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.facebook.com/reel/1033484732739023",
        "https://www.facebook.com/watch/?v=123",
        "https://www.facebook.com/share/r/abc123",
        "https://www.facebook.com/share/v/abc123",
        "https://www.facebook.com/someone/videos/123456",
        "https://fb.watch/abc123",
        "https://m.facebook.com/reel/123",
    ],
)
def test_accepts_facebook_video_urls(url: str) -> None:
    assert parse_facebook_video_url(url) == url


@pytest.mark.parametrize(
    "url, message",
    [
        ("http://www.facebook.com/reel/123", "must use https"),
        ("https://example.com/reel/123", "facebook.com, fb.com, or fb.watch"),
        ("https://www.facebook.com/someone", "reel, watch, share, or video"),
        ("https://fb.watch/", "missing the video id"),
    ],
)
def test_rejects_invalid_facebook_urls(url: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_facebook_video_url(url)

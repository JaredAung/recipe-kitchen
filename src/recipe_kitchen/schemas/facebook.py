from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

FACEBOOK_HOSTS = frozenset(
    {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "web.facebook.com",
        "mbasic.facebook.com",
        "fb.com",
        "www.fb.com",
        "m.fb.com",
        "fb.watch",
    }
)

_VIDEO_PATHS = (
    re.compile(r"^/reel/[^/]+", re.IGNORECASE),
    re.compile(r"^/reels/[^/]+", re.IGNORECASE),
    re.compile(r"^/watch/?", re.IGNORECASE),
    re.compile(r"^/share/r/[^/]+", re.IGNORECASE),
    re.compile(r"^/share/v/[^/]+", re.IGNORECASE),
    re.compile(r"^/[^/]+/videos/\d+", re.IGNORECASE),
    re.compile(r"^/[^/]+/reel/[^/]+", re.IGNORECASE),
)


def parse_facebook_video_url(url: str) -> str:
    """Return `url` if it is an https Facebook reel, watch, share, or video link.

    Checks host and path only. Does not prove the post exists or is public.
    Raises ValueError when the URL is not a Facebook video link.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        raise ValueError("Facebook URL must use https")
    host = (parsed.hostname or "").lower()
    if host not in FACEBOOK_HOSTS:
        raise ValueError("URL must be a facebook.com, fb.com, or fb.watch link")
    path = parsed.path or "/"
    if host == "fb.watch":
        if not path.strip("/"):
            raise ValueError("fb.watch URL is missing the video id")
        return url.strip()
    if not any(pattern.search(path) for pattern in _VIDEO_PATHS):
        raise ValueError("URL must be a Facebook reel, watch, share, or video link")
    return url.strip()


class FacebookMedia(BaseModel):
    video_id: str = ""
    source_url: str = ""
    caption: str = ""
    hd_url: str = ""
    sd_url: str = ""
    thumbnail_url: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    subtitles_url: str = ""
    audio_available: str = "Not available"
    creator_name: str = ""
    audio_title: str = ""

    @field_validator(
        "video_id",
        "source_url",
        "caption",
        "hd_url",
        "sd_url",
        "thumbnail_url",
        "subtitles_url",
        "creator_name",
        "audio_title",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: object) -> str:
        """Trim string fields. Missing or blank values become empty."""
        if not isinstance(value, str):
            return ""
        return value.strip()

    @field_validator("audio_available", mode="before")
    @classmethod
    def default_audio_available(cls, value: object) -> str:
        """Missing or blank audio status becomes Not available."""
        if not isinstance(value, str):
            return "Not available"
        return value.strip() or "Not available"

    @field_validator("duration", mode="before")
    @classmethod
    def coerce_duration(cls, value: object) -> float:
        """Missing or invalid duration becomes 0."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 0.0
        return float(value)

    @field_validator("width", "height", mode="before")
    @classmethod
    def coerce_dimension(cls, value: object) -> int:
        """Missing or invalid dimensions become 0."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 0
        return int(value)

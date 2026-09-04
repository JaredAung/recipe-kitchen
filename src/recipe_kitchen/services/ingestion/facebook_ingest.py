"""Scrape a Facebook video URL and store video, thumbnail, and subtitles."""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ValidationError

from recipe_kitchen.schemas.facebook import FacebookMedia
from recipe_kitchen.services.ingestion.cleaner import extract_facebook_media
from recipe_kitchen.services.ingestion.facebook_fetch import fetch_facebook
from recipe_kitchen.services.ingestion.subtitle_text import download_subtitle_text
from recipe_kitchen.services.ingestion.thumbnail_to_bucket import download_thumbnail
from recipe_kitchen.services.ingestion.video_to_bucket import download_video


class IngestMedia(BaseModel):
    video_id: str = ""
    source_url: str = ""
    caption: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    audio_available: str = "Not available"
    creator_name: str = ""
    audio_title: str = ""


class IngestResponse(BaseModel):
    media: IngestMedia
    video: str
    thumbnail: str = ""
    subtitle_text: str = ""


def _object_prefix(media: FacebookMedia) -> str:
    """Return a bucket prefix from the Facebook video id, or a random id."""
    return media.video_id or uuid4().hex


def run_facebook_ingest(url: str) -> IngestResponse:
    """Validate scrape output, store media, and return paths plus caption text."""
    try:
        media = extract_facebook_media(fetch_facebook(url))
    except ValidationError as exc:
        raise RuntimeError("Facebook scrape returned invalid media") from exc
    if not media.hd_url and not media.sd_url:
        raise RuntimeError("No video found at this Facebook URL")

    prefix = _object_prefix(media)
    video = download_video(
        media.sd_url or media.hd_url,
        f"{prefix}/video.mp4",
    ).path

    thumbnail = ""
    if media.thumbnail_url:
        try:
            thumbnail = download_thumbnail(
                media.thumbnail_url,
                f"{prefix}/thumbnail.jpg",
            ).path
        except RuntimeError, OSError:
            thumbnail = ""

    subtitle_text = ""
    if media.subtitles_url:
        try:
            subtitle_text = download_subtitle_text(media.subtitles_url)
        except RuntimeError, OSError:
            subtitle_text = ""

    return IngestResponse(
        media=IngestMedia.model_validate(media.model_dump()),
        video=video,
        thumbnail=thumbnail,
        subtitle_text=subtitle_text,
    )

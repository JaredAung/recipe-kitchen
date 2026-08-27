"""Accept a Facebook video URL, scrape it, and store video, thumbnail, and subtitles."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator

from recipe_kitchen.schemas.facebook import FacebookMedia, parse_facebook_video_url
from recipe_kitchen.services.ingestion.cleaner import extract_facebook_media
from recipe_kitchen.services.ingestion.facebook_fetch import fetch_facebook
from recipe_kitchen.services.ingestion.subtitle_text import download_subtitle_text
from recipe_kitchen.services.ingestion.thumbnail_to_bucket import download_thumbnail
from recipe_kitchen.services.ingestion.video_to_bucket import download_video

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def facebook_video_url(cls, value: HttpUrl) -> HttpUrl:
        """Reject non-Facebook and non-video URLs before the scrape runs."""
        parse_facebook_video_url(str(value))
        return value


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


@router.post("", response_model=IngestResponse)
def ingest_facebook(body: IngestRequest) -> IngestResponse:
    """Validate a Facebook video URL, scrape it, and store video, thumbnail, and subtitles."""
    url = str(body.url)
    try:
        media = extract_facebook_media(fetch_facebook(url))
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    if not media.hd_url and not media.sd_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No video found at this Facebook URL",
        )

    prefix = _object_prefix(media)
    try:
        video = download_video(
            media.sd_url or media.hd_url,
            f"{prefix}/video.mp4",
        ).path
    except (RuntimeError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

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

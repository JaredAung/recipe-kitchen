"""Accept a Facebook video URL and enqueue scrape + storage work."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl, field_validator

from recipe_kitchen.db.jobs import enqueue_job
from recipe_kitchen.schemas.facebook import parse_facebook_video_url
from recipe_kitchen.schemas.jobs import JobAccepted

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def facebook_video_url(cls, value: HttpUrl) -> HttpUrl:
        """Reject non-Facebook and non-video URLs before the job is queued."""
        parse_facebook_video_url(str(value))
        return value


@router.post("", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
def ingest_facebook(body: IngestRequest) -> JobAccepted:
    """Validate a Facebook video URL and enqueue ingest."""
    try:
        job_id = enqueue_job("ingest", {"url": str(body.url)})
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return JobAccepted(job_id=job_id)

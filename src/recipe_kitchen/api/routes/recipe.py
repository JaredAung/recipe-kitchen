"""Enqueue caption → subtitle → audio → visual extract."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from recipe_kitchen.db.jobs import enqueue_job
from recipe_kitchen.schemas.jobs import JobAccepted

router = APIRouter(prefix="/recipe", tags=["recipe"])


class RecipeExtractRequest(BaseModel):
    caption: str = ""
    subtitle_text: str = ""
    video: str = ""
    thumbnail: str = ""
    source_url: str | None = None
    original_filename: str | None = None


@router.post("", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
def extract_recipe(body: RecipeExtractRequest) -> JobAccepted:
    """Validate extract input and enqueue the recipe graph."""
    if not body.caption.strip() and not body.subtitle_text.strip() and not body.video.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a caption, subtitles, or an ingested video path.",
        )

    try:
        job_id = enqueue_job("recipe", body.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return JobAccepted(job_id=job_id)

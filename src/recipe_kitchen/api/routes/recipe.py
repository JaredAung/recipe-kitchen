"""Run caption → subtitle → audio → visual extract and save the recipe."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ValidationError

from recipe_kitchen.schemas.extract import RecipePipelineResult
from recipe_kitchen.services.recipe_pipeline import run_recipe_pipeline

router = APIRouter(prefix="/recipe", tags=["recipe"])


class RecipeExtractRequest(BaseModel):
    caption: str = ""
    subtitle_text: str = ""
    video: str = ""
    thumbnail: str = ""
    source_url: str | None = None
    original_filename: str | None = None


@router.post("", response_model=RecipePipelineResult)
def extract_recipe(body: RecipeExtractRequest) -> RecipePipelineResult:
    """Extract a recipe from caption, subtitles, and an ingested video.

    The stored video is downloaded only if the graph reaches the audio channel.
    """
    if not body.caption.strip() and not body.subtitle_text.strip() and not body.video.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a caption, subtitles, or an ingested video path.",
        )

    try:
        return run_recipe_pipeline(
            caption=body.caption,
            subtitle_text=body.subtitle_text,
            original_filename=body.original_filename
            or (Path(body.video).name if body.video.strip() else None),
            source_url=body.source_url,
            video_storage_path=body.video.strip() or None,
            thumbnail_path=body.thumbnail.strip() or None,
            save=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

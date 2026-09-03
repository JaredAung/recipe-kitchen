"""Run extract → transcribe → collect → translate → save on an uploaded recipe video."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ValidationError

from recipe_kitchen.api.uploads import save_upload
from recipe_kitchen.db.add_recipe import add_recipe
from recipe_kitchen.schemas.recipe import Ingredient, RecipeCreate, Step
from recipe_kitchen.services.audio_pipeline import extract_audio_channel

router = APIRouter(prefix="/audio", tags=["audio"])

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class AudioPipelineResponse(BaseModel):
    id: str
    transcript_my: str | None = None
    transcript_en: str
    ingredients: list[Ingredient]
    steps: list[Step]


def run_audio_pipeline(
    video_path: Path,
    *,
    original_filename: str | None = None,
) -> AudioPipelineResponse:
    """Transcribe, extract ingredients/steps, translate if Burmese, and save the recipe."""
    extracted = extract_audio_channel(video_path)
    saved = add_recipe(
        RecipeCreate(
            transcript_my=extracted.transcript_my,
            transcript_en=extracted.transcript_en,
            ingredients=extracted.ingredients,
            steps=extracted.steps,
            original_filename=original_filename,
        )
    )
    return AudioPipelineResponse(
        id=saved["id"],
        transcript_my=extracted.transcript_my,
        transcript_en=extracted.transcript_en,
        ingredients=extracted.ingredients,
        steps=extracted.steps,
    )


@router.post("", response_model=AudioPipelineResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Recipe video with spoken narration"),
) -> AudioPipelineResponse:
    """Accept a recipe video upload and run the audio extraction pipeline."""
    suffix = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if suffix not in VIDEO_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix}",
        )

    tmp_path = await save_upload(file, suffix=suffix)
    try:
        return run_audio_pipeline(tmp_path, original_filename=file.filename)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

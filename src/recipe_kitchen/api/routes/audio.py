"""Run extract → transcribe → translate → collect → save on an uploaded recipe video."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ValidationError

from recipe_kitchen.db.add_recipe import add_recipe
from recipe_kitchen.schemas.recipe import Ingredient, RecipeCreate, Step
from recipe_kitchen.services.audio_extractor import extract_pcm, pcm_to_wav
from recipe_kitchen.services.ingredient_collector import collect_ingredients
from recipe_kitchen.services.steps_collector import collect_steps
from recipe_kitchen.services.transcriber import transcribe_wav
from recipe_kitchen.services.translater import is_burmese, translate_to_english

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
    """Transcribe, translate if Burmese, extract ingredients/steps, and save the recipe."""
    pcm = extract_pcm(video_path)
    transcript = transcribe_wav(pcm_to_wav(pcm))
    if is_burmese(transcript):
        transcript_my = transcript
        transcript_en = translate_to_english(transcript)
    else:
        transcript_my = None
        transcript_en = transcript
    ingredients = collect_ingredients(transcript_en, source="audio")
    steps = collect_steps(transcript_en, source="audio")
    saved = add_recipe(
        RecipeCreate(
            transcript_my=transcript_my,
            transcript_en=transcript_en,
            ingredients=ingredients,
            steps=steps,
            original_filename=original_filename,
        )
    )
    return AudioPipelineResponse(
        id=saved["id"],
        transcript_my=transcript_my,
        transcript_en=transcript_en,
        ingredients=ingredients,
        steps=steps,
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

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

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

"""Run Gemini visual extract → save on an uploaded recipe video."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ValidationError

from recipe_kitchen.db.add_recipe import add_recipe
from recipe_kitchen.schemas.recipe import Ingredient, RecipeCreate, Step
from recipe_kitchen.services.visual_pipeline import MODEL, VIDEO_FPS, extract_visual_channel

router = APIRouter(prefix="/video", tags=["video"])

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class VideoPipelineResponse(BaseModel):
    id: str
    ingredients: list[Ingredient]
    steps: list[Step]
    usage: dict[str, Any] = {}


def run_video_pipeline(
    video_path: Path,
    *,
    original_filename: str | None = None,
) -> VideoPipelineResponse:
    """Extract visual ingredients/steps with Gemini and save the recipe."""
    extracted = extract_visual_channel(video_path)
    saved = add_recipe(
        RecipeCreate(
            transcript_en=extracted.transcript_en,
            ingredients=extracted.ingredients,
            steps=extracted.steps,
            original_filename=original_filename,
            extraction_meta={
                "channel": "visual",
                "model": MODEL,
                "fps": VIDEO_FPS,
                "usage": extracted.usage,
            },
        )
    )
    return VideoPipelineResponse(
        id=saved["id"],
        ingredients=extracted.ingredients,
        steps=extracted.steps,
        usage=extracted.usage,
    )


@router.post("", response_model=VideoPipelineResponse)
async def extract_video(
    file: UploadFile = File(..., description="Recipe video with on-screen ingredients or steps"),
) -> VideoPipelineResponse:
    """Accept a recipe video upload and run the visual extraction pipeline."""
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
        return run_video_pipeline(tmp_path, original_filename=file.filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

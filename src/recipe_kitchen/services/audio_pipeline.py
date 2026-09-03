"""Transcribe a recipe video and collect audio-channel ingredients and steps."""

from __future__ import annotations

from pathlib import Path

from recipe_kitchen.schemas.extract import AudioExtract
from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.audio_extractor import extract_pcm, pcm_to_wav
from recipe_kitchen.services.ingredient_collector import collect_ingredients
from recipe_kitchen.services.steps_collector import collect_steps
from recipe_kitchen.services.transcriber import transcribe_wav
from recipe_kitchen.services.translater import is_burmese, translate_to_english


def extract_audio_channel(video_path: Path) -> AudioExtract:
    """Transcribe, translate if Burmese, and collect ingredients and steps.

    Does not save a recipe.
    """
    pcm = extract_pcm(video_path)
    transcript = transcribe_wav(pcm_to_wav(pcm))
    if is_burmese(transcript):
        transcript_my = transcript
        transcript_en = translate_to_english(transcript)
    else:
        transcript_my = None
        transcript_en = transcript
    ingredients = [
        Ingredient.model_validate(item)
        for item in collect_ingredients(transcript_en, source="audio")
    ]
    steps = [Step.model_validate(item) for item in collect_steps(transcript_en, source="audio")]
    return AudioExtract(
        transcript_my=transcript_my,
        transcript_en=transcript_en,
        ingredients=ingredients,
        steps=steps,
    )

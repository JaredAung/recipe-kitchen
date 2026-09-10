"""Transcribe a recipe video and collect audio-channel ingredients and steps."""

from __future__ import annotations

import logging
from pathlib import Path

from recipe_kitchen.schemas.extract import AudioExtract
from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.audio_extractor import extract_pcm, pcm_to_wav
from recipe_kitchen.services.collect_bilingual import collect_bilingual
from recipe_kitchen.services.ingredient_collector import collect_ingredients
from recipe_kitchen.services.speech_vad import has_speech
from recipe_kitchen.services.steps_collector import collect_steps
from recipe_kitchen.services.transcriber import transcribe_wav
from recipe_kitchen.services.translater import is_burmese, translate_to_english

logger = logging.getLogger(__name__)


def extract_audio_channel(video_path: Path) -> AudioExtract:
    """Transcribe, collect, then translate if Burmese.

    Skips speech-to-text when Silero VAD finds no speech. Does not save a recipe.
    Burmese speech is collected from the original transcript and the English
    translation in parallel, then reconciled before the judge.
    """
    pcm = extract_pcm(video_path)
    if not has_speech(pcm):
        logger.info("No speech detected; skipping STT")
        return AudioExtract(transcript_en="", ingredients=[], steps=[])
    logger.info("Speech detected; transcribing")
    transcript = transcribe_wav(pcm_to_wav(pcm))
    if is_burmese(transcript):
        transcript_en = translate_to_english(transcript)
        logger.info("Burmese audio: collecting original and English in parallel")
        ingredients, steps = collect_bilingual(transcript, transcript_en, source="audio")
        return AudioExtract(
            transcript_my=transcript,
            transcript_en=transcript_en,
            ingredients=ingredients,
            steps=steps,
        )
    ingredients = [
        Ingredient.model_validate(item) for item in collect_ingredients(transcript, source="audio")
    ]
    steps = [Step.model_validate(item) for item in collect_steps(transcript, source="audio")]
    return AudioExtract(
        transcript_en=transcript,
        ingredients=ingredients,
        steps=steps,
    )

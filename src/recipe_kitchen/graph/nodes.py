"""LangGraph nodes: extract, judge, enrich, then save."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Literal

from recipe_kitchen.db.add_recipe import add_recipe
from recipe_kitchen.graph.temp_video import register_temp_video
from recipe_kitchen.schemas.extract import CaptionExtract, RecipeGraphState
from recipe_kitchen.schemas.recipe import RecipeCreate
from recipe_kitchen.services.audio_pipeline import extract_audio_channel
from recipe_kitchen.services.caption_pipeline import (
    english_caption_text,
    extract_caption_channel,
)
from recipe_kitchen.services.completeness import is_sufficient
from recipe_kitchen.services.extract_merge import merge_ingredients, merge_steps
from recipe_kitchen.services.ingestion.video_to_bucket import fetch_stored_video
from recipe_kitchen.services.recipe_metadata import extract_recipe_metadata
from recipe_kitchen.services.validation_tools import audit_extract, source_corpus
from recipe_kitchen.services.visual_pipeline import extract_visual_channel

StartRoute = Literal["caption", "subtitle", "audio", "__end__"]
AfterJudgeRoute = Literal["enrich", "subtitle", "audio", "visual", "__end__"]
AfterAudioRoute = Literal["judge", "visual"]

logger = logging.getLogger(__name__)


def _has_video(state: RecipeGraphState) -> bool:
    """True when a local video or a stored object can be used."""
    return bool(state.video_path or state.video_storage_path)


def route_start(state: RecipeGraphState) -> StartRoute:
    """Pick the first channel that has input."""
    if state.caption.strip():
        nxt: StartRoute = "caption"
    elif state.subtitle_text.strip():
        nxt = "subtitle"
    elif _has_video(state):
        nxt = "audio"
    else:
        nxt = "__end__"
    logger.info("Graph start -> %s", nxt)
    return nxt


def route_after_judge(state: RecipeGraphState) -> AfterJudgeRoute:
    """Enrich when sufficient; otherwise take the next channel or stop."""
    if state.sufficient:
        nxt: AfterJudgeRoute = "enrich"
    elif state.phase == "caption" and state.subtitle_text.strip():
        nxt = "subtitle"
    elif state.phase in {"caption", "subtitle"} and _has_video(state):
        nxt = "audio"
    elif state.phase == "audio" and _has_video(state):
        nxt = "visual"
    else:
        nxt = "__end__"
    logger.info("After %s judge (sufficient=%s) -> %s", state.phase, state.sufficient, nxt)
    return nxt


def route_after_audio(state: RecipeGraphState) -> AfterAudioRoute:
    """Skip the audio judge when VAD found no speech; go straight to visual."""
    if not state.audio_has_speech and _has_video(state):
        nxt: AfterAudioRoute = "visual"
    else:
        nxt = "judge"
    logger.info("After audio (speech=%s) -> %s", state.audio_has_speech, nxt)
    return nxt


def _source_text(state: RecipeGraphState) -> str:
    """Text the judge should see for channels run so far."""
    parts = [state.caption, state.subtitle_text]
    if state.phase in {"audio", "visual"}:
        parts.append(state.transcript_en)
    if state.phase == "visual":
        parts.append(state.visual_text)
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _local_video(state: RecipeGraphState) -> str:
    """Return a filesystem path, fetching from storage once if needed."""
    if state.video_path:
        logger.info("Using local video %s", state.video_path)
        return state.video_path
    if not state.video_storage_path:
        raise ValueError("No video was provided for audio or visual extract.")
    logger.info("Fetching stored video %s", state.video_storage_path)
    data = fetch_stored_video(state.video_storage_path)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    register_temp_video(Path(path))
    logger.info("Stored video saved to %s (%s bytes)", path, len(data))
    return path


def caption_node(state: RecipeGraphState) -> dict[str, Any]:
    """Extract ingredients and steps from the Facebook post caption."""
    logger.info("Caption extract starting (%s chars)", len(state.caption))
    extracted = extract_caption_channel(state.caption, source="caption")
    logger.info(
        "Caption extract done: %s ingredients, %s steps",
        len(extracted.ingredients),
        len(extracted.steps),
    )
    return {
        "phase": "caption",
        "ingredients": merge_ingredients([], extracted.ingredients),
        "steps": merge_steps([], extracted.steps),
        "transcript_my": extracted.text_my,
        "transcript_en": extracted.text_en,
        "text_my": extracted.text_my,
        "text_en": extracted.text_en,
    }


def subtitle_node(state: RecipeGraphState) -> dict[str, Any]:
    """Extract from Facebook subtitles and merge with any caption extract."""
    logger.info("Subtitle extract starting (%s chars)", len(state.subtitle_text))
    extracted = extract_caption_channel(state.subtitle_text, source="caption")
    logger.info(
        "Subtitle extract done: +%s ingredients, +%s steps",
        len(extracted.ingredients),
        len(extracted.steps),
    )
    return {
        "phase": "subtitle",
        "ingredients": merge_ingredients(state.ingredients, extracted.ingredients),
        "steps": merge_steps(state.steps, extracted.steps),
        "transcript_my": extracted.text_my or state.transcript_my,
        "transcript_en": extracted.text_en or state.transcript_en,
        "text_my": extracted.text_my,
        "text_en": extracted.text_en,
    }


def audio_node(state: RecipeGraphState) -> dict[str, Any]:
    """Fetch the video if needed, transcribe when VAD finds speech, merge extracts."""
    if not _has_video(state):
        raise ValueError(
            "Caption and subtitles were not enough, and no video was provided for audio."
        )
    video_path = _local_video(state)
    logger.info("Audio extract starting")
    audio = extract_audio_channel(Path(video_path))
    if audio.transcript_en.strip():
        logger.info(
            "Audio extract done: %s ingredients, %s steps",
            len(audio.ingredients),
            len(audio.steps),
        )
    else:
        logger.info("Audio extract done with no transcript")
    spoken = bool(audio.transcript_en.strip())
    update: dict[str, Any] = {
        "phase": "audio",
        "video_path": video_path,
        "audio_has_speech": spoken,
        "ingredients": merge_ingredients(state.ingredients, audio.ingredients),
        "steps": merge_steps(state.steps, audio.steps),
    }
    if spoken:
        update["transcript_my"] = audio.transcript_my
        update["transcript_en"] = audio.transcript_en
        update["text_my"] = audio.transcript_my
        update["text_en"] = audio.transcript_en
    return update


def visual_node(state: RecipeGraphState) -> dict[str, Any]:
    """Read on-screen text from the video fetched in the audio node."""
    if not state.video_path:
        raise ValueError("Audio was not enough, and no local video was available for visual.")
    logger.info("Visual extract starting")
    visual = extract_visual_channel(Path(state.video_path))
    logger.info(
        "Visual extract done: +%s ingredients, +%s steps confidence=%s",
        len(visual.ingredients),
        len(visual.steps),
        visual.confidence,
    )
    return {
        "phase": "visual",
        "ingredients": merge_ingredients(state.ingredients, visual.ingredients),
        "steps": merge_steps(state.steps, visual.steps),
        "visual_text": visual.transcript_en,
    }


def sufficiency_node(state: RecipeGraphState) -> dict[str, Any]:
    """Ask whether a cook could recreate the dish from the current extract."""
    judgment = is_sufficient(
        state.ingredients,
        state.steps,
        source_text=_source_text(state),
    )
    logger.info(
        "Judge after %s: sufficient=%s (%s)",
        state.phase,
        judgment.sufficient,
        judgment.reason,
    )
    return {"sufficient": judgment.sufficient, "reason": judgment.reason}


def enrich_node(state: RecipeGraphState) -> dict[str, Any]:
    """Name the dish, set cuisine, and flag grounding or generic-name issues.

    Does not change `sufficient` or send the graph back to another channel.
    """
    issues, confidence = audit_extract(
        state.ingredients,
        state.steps,
        corpus=source_corpus(
            caption=state.caption,
            subtitle_text=state.subtitle_text,
            transcript_en=state.transcript_en,
            transcript_my=state.transcript_my,
            text_en=state.text_en,
            text_my=state.text_my,
        ),
    )
    metadata = extract_recipe_metadata(state.ingredients, state.steps)
    logger.info(
        "Enrich after %s: title=%r cuisine=%s tags=%s time=%s issues=%s confidence=%s",
        state.phase,
        metadata.title,
        metadata.cuisine,
        metadata.tags,
        metadata.total_time_minutes,
        len(issues),
        confidence,
    )
    return {
        "title": metadata.title,
        "cuisine": metadata.cuisine,
        "description": metadata.description,
        "tags": metadata.tags,
        "total_time_minutes": metadata.total_time_minutes,
        "validation_issues": issues,
        "validation_confidence": confidence,
    }


def english_transcript(state: RecipeGraphState) -> str:
    """English transcript to store: translate caption text, else keep or fall back."""
    if state.phase in {"caption", "subtitle"}:
        return english_caption_text(
            CaptionExtract(
                ingredients=state.ingredients,
                steps=state.steps,
                source_text=state.caption or state.subtitle_text,
                text_my=state.text_my,
                text_en=state.text_en,
            )
        )
    if state.transcript_en.strip():
        return state.transcript_en
    return state.visual_text or "Recipe extract."


def save_node(state: RecipeGraphState) -> dict[str, Any]:
    """Persist a sufficient extract. Skips the database when `save` is false."""
    if state.phase is None:
        raise RuntimeError("Cannot save a recipe before an extract channel ran.")
    transcript_en = english_transcript(state)
    update: dict[str, Any] = {"transcript_en": transcript_en}
    if not state.save:
        logger.info("Skip save after %s (save=False)", state.phase)
        return update
    saved = add_recipe(
        RecipeCreate(
            transcript_my=state.transcript_my,
            transcript_en=transcript_en,
            ingredients=state.ingredients,
            steps=state.steps,
            title=state.title.strip() or None,
            description=state.description.strip() or None,
            cuisine=state.cuisine.strip(),
            tags=state.tags,
            total_time_minutes=state.total_time_minutes,
            original_filename=state.original_filename,
            source_url=state.source_url,
            video_path=state.video_storage_path,
            thumbnail_path=state.thumbnail_path,
            caption_text=state.caption,
            extraction_meta={
                "stopped_after": state.phase,
                "sufficient": state.sufficient,
                "reason": state.reason,
                "subtitle_text": state.subtitle_text,
                "validation_issues": [issue.model_dump() for issue in state.validation_issues],
                "validation_confidence": state.validation_confidence,
            },
        )
    )
    recipe_id = str(saved["id"])
    logger.info("Saved recipe %s after %s", recipe_id, state.phase)
    update["recipe_id"] = recipe_id
    return update

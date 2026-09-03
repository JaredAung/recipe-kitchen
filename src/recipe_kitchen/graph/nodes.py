"""LangGraph nodes: extract a channel or judge whether the extract is enough."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Literal

from recipe_kitchen.graph.temp_video import register_temp_video
from recipe_kitchen.schemas.extract import RecipeGraphState
from recipe_kitchen.services.audio_pipeline import extract_audio_channel
from recipe_kitchen.services.caption_pipeline import extract_caption_channel
from recipe_kitchen.services.completeness import is_sufficient
from recipe_kitchen.services.ingestion.video_to_bucket import fetch_stored_video
from recipe_kitchen.services.visual_pipeline import extract_visual_channel

StartRoute = Literal["caption", "subtitle", "audio", "__end__"]
AfterJudgeRoute = Literal["subtitle", "audio", "visual", "__end__"]

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
    """Stop when sufficient or after visual; otherwise take the next channel."""
    if state.sufficient or state.phase == "visual":
        nxt: AfterJudgeRoute = "__end__"
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
        "ingredients": extracted.ingredients,
        "steps": extracted.steps,
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
        "ingredients": [*state.ingredients, *extracted.ingredients],
        "steps": [*state.steps, *extracted.steps],
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
    update: dict[str, Any] = {
        "phase": "audio",
        "video_path": video_path,
        "ingredients": [*state.ingredients, *audio.ingredients],
        "steps": [*state.steps, *audio.steps],
    }
    if audio.transcript_en.strip():
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
        "Visual extract done: +%s ingredients, +%s steps",
        len(visual.ingredients),
        len(visual.steps),
    )
    return {
        "phase": "visual",
        "ingredients": [*state.ingredients, *visual.ingredients],
        "steps": [*state.steps, *visual.steps],
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

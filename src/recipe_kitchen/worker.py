"""Claim SQS job ids and run ingest / recipe / audio / visual pipelines."""

from __future__ import annotations

import logging
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from recipe_kitchen.api.routes.audio import run_audio_pipeline
from recipe_kitchen.api.routes.video import run_video_pipeline
from recipe_kitchen.db.jobs import claim_job, fail_job, finish_job
from recipe_kitchen.queue.sqs import delete_message, receive
from recipe_kitchen.schemas.jobs import Job
from recipe_kitchen.services.ingestion.facebook_ingest import run_facebook_ingest
from recipe_kitchen.services.ingestion.video_to_bucket import delete_video, fetch_stored_video
from recipe_kitchen.services.recipe_pipeline import run_recipe_pipeline

logger = logging.getLogger(__name__)


def _text(payload: Mapping[str, Any], key: str) -> str:
    """Return a stripped string field from a job payload."""
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""


def _optional_text(payload: Mapping[str, Any], key: str) -> str | None:
    """Return a stripped string field, or `None` when missing or blank."""
    text = _text(payload, key)
    return text or None


def _handle_recipe(job: Job) -> None:
    """Run the recipe graph and store `RecipePipelineResult`."""
    payload = job.input
    video = _text(payload, "video")
    original = _optional_text(payload, "original_filename") or (Path(video).name if video else None)
    result = run_recipe_pipeline(
        caption=_text(payload, "caption"),
        subtitle_text=_text(payload, "subtitle_text"),
        original_filename=original,
        source_url=_optional_text(payload, "source_url"),
        video_storage_path=video or None,
        thumbnail_path=_optional_text(payload, "thumbnail"),
        save=True,
    )
    finish_job(job.id, result.model_dump(mode="json"))


def _handle_ingest(job: Job) -> None:
    """Scrape Facebook and store video, thumbnail, and subtitles."""
    url = _text(job.input, "url")
    if not url:
        raise ValueError("Ingest job is missing a url.")
    result = run_facebook_ingest(url)
    finish_job(job.id, result.model_dump(mode="json"))


def _with_stored_video(object_path: str, suffix: str) -> Path:
    """Download a stored object to a temp file."""
    data = fetch_stored_video(object_path)
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
    finally:
        tmp.close()
    return Path(tmp.name)


def _handle_stored_pipeline(job: Job, kind: str) -> None:
    """Download an uploaded video, run audio or visual extract, then delete it."""
    object_path = _text(job.input, "video")
    if not object_path:
        raise ValueError(f"{kind} job is missing a video path.")
    suffix = Path(object_path).suffix.lower() or ".mp4"
    original = _optional_text(job.input, "original_filename")
    tmp_path = _with_stored_video(object_path, suffix)
    try:
        if kind == "audio":
            result = run_audio_pipeline(tmp_path, original_filename=original)
        else:
            result = run_video_pipeline(tmp_path, original_filename=original)
        finish_job(job.id, result.model_dump(mode="json"))
    finally:
        tmp_path.unlink(missing_ok=True)
        try:
            delete_video(object_path)
        except RuntimeError:
            logger.exception("Failed to delete stored video %s", object_path)


def handle_job(job: Job) -> None:
    """Dispatch a claimed job to the matching pipeline."""
    logger.info("Job %s start kind=%s", job.id, job.kind)
    if job.kind == "recipe":
        _handle_recipe(job)
    elif job.kind == "ingest":
        _handle_ingest(job)
    elif job.kind in {"audio", "video"}:
        _handle_stored_pipeline(job, job.kind)
    else:
        raise ValueError(f"Unknown job kind: {job.kind}")
    logger.info("Job %s succeeded kind=%s", job.id, job.kind)


def process_message(job_id: str) -> None:
    """Claim, run, and finish a job. Application errors are stored, not retried."""
    job = claim_job(job_id)
    if job is None:
        logger.info("Job %s skipped (missing or already finished)", job_id)
        return
    try:
        handle_job(job)
    except Exception:
        logger.exception("Job %s failed kind=%s", job.id, job.kind)
        fail_job(job.id, "pipeline_failed")


def run_forever() -> None:
    """Long-poll SQS and process one job at a time."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("Worker listening for jobs")
    while True:
        try:
            messages = receive()
        except Exception:
            logger.exception("SQS receive failed")
            time.sleep(5)
            continue
        for message in messages:
            try:
                process_message(message.job_id)
            finally:
                try:
                    delete_message(message.receipt_handle)
                except Exception:
                    logger.exception("Failed to delete SQS message for job %s", message.job_id)


def main() -> None:
    """Entry point for `python -m recipe_kitchen.worker`."""
    run_forever()


if __name__ == "__main__":
    main()

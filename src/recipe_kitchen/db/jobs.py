"""Insert, claim, and finish async jobs. SQS only carries the job id."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from postgrest.exceptions import APIError

from recipe_kitchen.db.supabase import get_supabase_admin
from recipe_kitchen.queue.sqs import enqueue
from recipe_kitchen.schemas.jobs import Job, JobKind
from recipe_kitchen.services.ingestion.video_to_bucket import delete_video, upload_local_video


def _execute(result: Any, action: str) -> list[dict[str, Any]]:
    """Return rows from a Supabase response, or raise on failure."""
    error = getattr(result, "error", None)
    if error:
        raise RuntimeError(f"Failed to {action}: {error}")
    data = result.data or []
    if not data:
        raise RuntimeError(f"Failed to {action}: empty response")
    return data


def _job(row: dict[str, Any]) -> Job:
    """Build a `Job` from a jobs table row."""
    return Job(
        id=str(row["id"]),
        kind=row["kind"],
        status=row["status"],
        input=row.get("input") or {},
        result=row.get("result"),
        error=row.get("error") or "",
    )


def enqueue_job(kind: JobKind, payload: dict[str, Any]) -> str:
    """Insert a queued job, publish its id to SQS, and return the id.

    Deletes the row if SQS send fails so the client can retry the POST.
    """
    try:
        inserted = _execute(
            get_supabase_admin()
            .table("jobs")
            .insert({"kind": kind, "status": "queued", "input": payload})
            .execute(),
            "insert job",
        )
    except APIError as exc:
        raise RuntimeError(f"Failed to insert job: {exc}") from exc
    job_id = str(inserted[0]["id"])
    try:
        enqueue(job_id)
    except Exception:
        get_supabase_admin().table("jobs").delete().eq("id", job_id).execute()
        raise RuntimeError("Failed to enqueue job") from None
    return job_id


def enqueue_upload_job(
    kind: JobKind,
    tmp_path: Path,
    *,
    suffix: str,
    original_filename: str | None,
) -> str:
    """Upload a local video, enqueue an audio/video job, and return the job id.

    Removes the object if enqueue fails after the upload.
    """
    object_path = f"uploads/{uuid4().hex}/video{suffix}"
    upload_local_video(tmp_path, object_path)
    try:
        return enqueue_job(
            kind,
            {"video": object_path, "original_filename": original_filename},
        )
    except Exception:
        delete_video(object_path)
        raise


def fetch_job(job_id: str) -> Job | None:
    """Return a job by id, or `None` if it does not exist."""
    try:
        result = (
            get_supabase_admin().table("jobs").select("*").eq("id", job_id).limit(1).execute()
        )
    except APIError as exc:
        raise RuntimeError(f"Failed to fetch job: {exc}") from exc
    error = getattr(result, "error", None)
    if error:
        raise RuntimeError(f"Failed to fetch job: {error}")
    rows = result.data or []
    if not rows:
        return None
    row = rows[0]
    if not isinstance(row, dict):
        raise RuntimeError("Failed to fetch job: unexpected row")
    return _job(row)


def claim_job(job_id: str) -> Job | None:
    """Mark a queued or running job as running. Returns `None` if it is done."""
    job = fetch_job(job_id)
    if job is None or job.status in {"succeeded", "failed"}:
        return None
    updated = (
        get_supabase_admin()
        .table("jobs")
        .update({"status": "running"})
        .eq("id", job_id)
        .select("*")
        .execute()
    )
    error = getattr(updated, "error", None)
    if error:
        raise RuntimeError(f"Failed to claim job: {error}")
    claimed = fetch_job(job_id)
    if claimed is None or claimed.status in {"succeeded", "failed"}:
        return None
    return claimed


def finish_job(job_id: str, result: dict[str, Any]) -> None:
    """Store a successful job result."""
    _execute(
        get_supabase_admin()
        .table("jobs")
        .update({"status": "succeeded", "result": result, "error": ""})
        .eq("id", job_id)
        .select("id")
        .execute(),
        "finish job",
    )


def fail_job(job_id: str, error: str) -> None:
    """Mark a job failed without retrying paid pipeline work."""
    _execute(
        get_supabase_admin()
        .table("jobs")
        .update({"status": "failed", "error": error})
        .eq("id", job_id)
        .select("id")
        .execute(),
        "fail job",
    )

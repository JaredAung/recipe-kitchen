"""Poll async job status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from recipe_kitchen.db.jobs import fetch_job
from recipe_kitchen.schemas.jobs import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    """Return the current status and result of a job."""
    job = fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobStatus(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        result=job.result,
        error=job.error,
    )

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

JobKind = Literal["ingest", "recipe", "audio", "video"]
JobState = Literal["queued", "running", "succeeded", "failed"]


class JobAccepted(BaseModel):
    job_id: str


class Job(BaseModel):
    id: str
    kind: JobKind
    status: JobState
    input: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    error: str = ""


class JobStatus(BaseModel):
    job_id: str
    kind: JobKind
    status: JobState
    result: dict[str, Any] | None = None
    error: str = ""

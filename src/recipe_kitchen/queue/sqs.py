"""SQS send/receive for job ids. Job payloads live in the jobs table."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, NamedTuple

import boto3

from recipe_kitchen.core.config import get_settings

VISIBILITY_TIMEOUT_SECONDS = 900


class SqsMessage(NamedTuple):
    job_id: str
    receipt_handle: str


@lru_cache
def _client() -> Any:
    """Return a cached SQS client for the configured region."""
    return boto3.client("sqs", region_name=get_settings().aws_region)


def _queue_url() -> str:
    """Return the jobs queue URL, or raise if it is not configured."""
    url = get_settings().sqs_queue_url.strip()
    if not url:
        raise RuntimeError("SQS_QUEUE_URL is missing")
    return url


def enqueue(job_id: str) -> None:
    """Put `job_id` on the jobs queue."""
    _client().send_message(
        QueueUrl=_queue_url(),
        MessageBody=json.dumps({"job_id": job_id}),
    )


def receive(
    *,
    wait_seconds: int = 20,
    visibility_timeout: int = VISIBILITY_TIMEOUT_SECONDS,
) -> list[SqsMessage]:
    """Long-poll SQS and return messages that contain a job id."""
    response = _client().receive_message(
        QueueUrl=_queue_url(),
        MaxNumberOfMessages=1,
        WaitTimeSeconds=wait_seconds,
        VisibilityTimeout=visibility_timeout,
    )
    messages: list[SqsMessage] = []
    for raw in response.get("Messages") or []:
        handle = raw.get("ReceiptHandle")
        if not isinstance(handle, str) or not handle:
            continue
        try:
            body = json.loads(raw.get("Body") or "")
            job_id = str(body["job_id"])
        except json.JSONDecodeError, KeyError, TypeError:
            delete_message(handle)
            continue
        if not job_id:
            delete_message(handle)
            continue
        messages.append(SqsMessage(job_id=job_id, receipt_handle=handle))
    return messages


def delete_message(receipt_handle: str) -> None:
    """Remove a received message from the queue."""
    _client().delete_message(QueueUrl=_queue_url(), ReceiptHandle=receipt_handle)

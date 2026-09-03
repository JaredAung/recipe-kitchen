"""Collect per-service latency and token counts during a recipe graph run."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_usage_calls: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "recipe_usage_calls",
    default=None,
)


@contextmanager
def collect_usage() -> Iterator[list[dict[str, Any]]]:
    """Record API usage for the current graph run."""
    calls: list[dict[str, Any]] = []
    token = _usage_calls.set(calls)
    try:
        yield calls
    finally:
        _usage_calls.reset(token)


def usage_from_gemini_rest(body: dict[str, Any]) -> dict[str, int]:
    """Copy token counts from a Gemini REST `usageMetadata` object."""
    raw = body.get("usageMetadata") or {}
    usage = {
        "prompt_token_count": int(raw.get("promptTokenCount") or 0),
        "candidates_token_count": int(raw.get("candidatesTokenCount") or 0),
        "total_token_count": int(raw.get("totalTokenCount") or 0),
    }
    thoughts = raw.get("thoughtsTokenCount")
    if thoughts is not None:
        usage["thoughts_token_count"] = int(thoughts)
    return usage


def record_usage(
    service: str,
    *,
    elapsed_seconds: float,
    prompt_token_count: int = 0,
    candidates_token_count: int = 0,
    thoughts_token_count: int = 0,
    total_token_count: int = 0,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append one API call if a `collect_usage` block is active."""
    bucket = _usage_calls.get()
    if bucket is None:
        return
    call: dict[str, Any] = {
        "service": service,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "prompt_token_count": prompt_token_count,
        "candidates_token_count": candidates_token_count,
        "total_token_count": total_token_count,
    }
    if thoughts_token_count:
        call["thoughts_token_count"] = thoughts_token_count
    if extra:
        call["extra"] = extra
    bucket.append(call)


def record_token_usage(
    service: str,
    elapsed_seconds: float,
    usage: dict[str, int],
) -> None:
    """Record token counts from a Gemini usage dict."""
    record_usage(
        service,
        elapsed_seconds=elapsed_seconds,
        prompt_token_count=usage.get("prompt_token_count", 0),
        candidates_token_count=usage.get("candidates_token_count", 0),
        total_token_count=usage.get("total_token_count", 0),
        thoughts_token_count=usage.get("thoughts_token_count", 0),
    )


def record_gemini_rest(service: str, body: dict[str, Any], elapsed_seconds: float) -> None:
    """Record Gemini REST usage for `service`."""
    record_token_usage(service, elapsed_seconds, usage_from_gemini_rest(body))


def summarize_usage(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Group calls by service and sum latency and tokens."""
    by_service: dict[str, dict[str, Any]] = {}
    total: dict[str, Any] = {
        "calls": 0,
        "elapsed_seconds": 0.0,
        "prompt_token_count": 0,
        "candidates_token_count": 0,
        "total_token_count": 0,
    }
    for call in calls:
        name = str(call["service"])
        bucket = by_service.setdefault(
            name,
            {
                "calls": 0,
                "elapsed_seconds": 0.0,
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0,
            },
        )
        elapsed = float(call.get("elapsed_seconds") or 0)
        prompt = int(call.get("prompt_token_count") or 0)
        candidates = int(call.get("candidates_token_count") or 0)
        tokens = int(call.get("total_token_count") or 0)
        bucket["calls"] += 1
        bucket["elapsed_seconds"] = round(float(bucket["elapsed_seconds"]) + elapsed, 3)
        bucket["prompt_token_count"] = int(bucket["prompt_token_count"]) + prompt
        bucket["candidates_token_count"] = int(bucket["candidates_token_count"]) + candidates
        bucket["total_token_count"] = int(bucket["total_token_count"]) + tokens
        total["calls"] += 1
        total["elapsed_seconds"] = round(float(total["elapsed_seconds"]) + elapsed, 3)
        total["prompt_token_count"] += prompt
        total["candidates_token_count"] += candidates
        total["total_token_count"] += tokens
        thoughts = call.get("thoughts_token_count")
        if thoughts:
            bucket["thoughts_token_count"] = int(bucket.get("thoughts_token_count") or 0) + int(
                thoughts
            )
            total["thoughts_token_count"] = int(total.get("thoughts_token_count") or 0) + int(
                thoughts
            )
    return {"by_service": by_service, "total": total, "calls": calls}

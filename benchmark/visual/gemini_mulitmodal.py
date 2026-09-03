"""Extract ingredients and steps from test6.mp4 with Gemini multimodal models."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEO_PATH = ROOT / "testing-material" / "test6.mp4"
OUTPUT_DIR = Path(__file__).resolve().parent / "results"
MODELS = ("gemini-3.5-flash-lite", "gemini-3.8-flash")

PROMPT = """Watch this cooking video. Extract ingredients and steps from what you can see:
on-screen text, packaging labels, and cooking actions.

This is the visual channel of a recipe video. There may be no spoken recipe.

For each ingredient return:
- name: common kitchen name in English
- amount: quantity and unit if shown, otherwise an empty string
- evidence: a short description of the on-screen text or visible action

For each step return:
- order: 1-based sequence number
- instruction: a clear English cooking action
- evidence: a short description of the on-screen text or visible action

Rules:
- Only list things used as ingredients, not utensils, cookware, or the finished dish.
- Deduplicate the same ingredient. Merge amounts if it is shown more than once.
- Keep steps in the order they happen.
- Split distinct actions into separate steps.
- Do not invent ingredients, amounts, or steps that are not visible.
- Return JSON only.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "ingredients": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "amount": {"type": "STRING"},
                    "evidence": {"type": "STRING"},
                },
                "required": ["name", "amount", "evidence"],
            },
        },
        "steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "order": {"type": "INTEGER"},
                    "instruction": {"type": "STRING"},
                    "evidence": {"type": "STRING"},
                },
                "required": ["order", "instruction", "evidence"],
            },
        },
    },
    "required": ["ingredients", "steps"],
}


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit("GEMINI_API_KEY is missing. Set it in .env")
    return key


def parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini returned invalid JSON: {raw}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Gemini returned unexpected JSON: {raw}")
    return parsed


def usage_from_body(body: dict) -> dict:
    """Copy Gemini usageMetadata into a JSON-friendly dict."""
    raw = body.get("usageMetadata") or {}
    details = []
    for item in raw.get("promptTokensDetails") or []:
        details.append(
            {
                "modality": str(item.get("modality") or ""),
                "token_count": int(item.get("tokenCount") or 0),
            }
        )
    usage = {
        "prompt_token_count": int(raw.get("promptTokenCount") or 0),
        "candidates_token_count": int(raw.get("candidatesTokenCount") or 0),
        "thoughts_token_count": int(raw.get("thoughtsTokenCount") or 0),
        "total_token_count": int(raw.get("totalTokenCount") or 0),
        "prompt_tokens_details": details,
    }
    cached = raw.get("cachedContentTokenCount")
    if cached is not None:
        usage["cached_content_token_count"] = int(cached)
    return usage


def format_usage(usage: dict) -> str:
    """One-line token summary for stdout."""
    parts = [
        f"prompt={usage['prompt_token_count']}",
        f"output={usage['candidates_token_count']}",
        f"total={usage['total_token_count']}",
    ]
    if usage.get("thoughts_token_count"):
        parts.append(f"thoughts={usage['thoughts_token_count']}")
    by_modality = [
        f"{item['modality'].lower()}={item['token_count']}"
        for item in usage.get("prompt_tokens_details") or []
        if item.get("token_count")
    ]
    if by_modality:
        parts.append("input[" + " ".join(by_modality) + "]")
    return " ".join(parts)


def stamp_visual(extracted: dict) -> dict:
    ingredients = []
    for item in extracted.get("ingredients") or []:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        ingredients.append(
            {
                "name": name,
                "amount": str(item.get("amount") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
                "source": "visual",
            }
        )
    steps = []
    for item in extracted.get("steps") or []:
        instruction = str(item.get("instruction") or "").strip()
        if not instruction:
            continue
        try:
            order = int(item.get("order") or 0)
        except (TypeError, ValueError):
            order = 0
        steps.append(
            {
                "order": order,
                "instruction": instruction,
                "evidence": str(item.get("evidence") or "").strip(),
                "source": "visual",
            }
        )
    steps.sort(key=lambda step: step["order"] or 10**9)
    for index, step in enumerate(steps, start=1):
        if step["order"] < 1:
            step["order"] = index
    return {"ingredients": ingredients, "steps": steps}


def extract(api_key: str, model: str, video_b64: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": "video/mp4", "data": video_b64}},
                    {"text": PROMPT},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "mediaResolution": "MEDIA_RESOLUTION_HIGH",
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{model} HTTP {exc.code}: {detail}") from exc

    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = "".join(part.get("text", "") for part in parts).strip()
    if not raw:
        raise RuntimeError(f"{model} returned no text: {body}")
    result = stamp_visual(parse_json(raw))
    result["usage"] = usage_from_body(body)
    return result


def main() -> None:
    load_env(ROOT / ".env")
    if not VIDEO_PATH.is_file():
        sys.exit(f"Video not found: {VIDEO_PATH}")

    video_b64 = base64.b64encode(VIDEO_PATH.read_bytes()).decode("ascii")
    api_key = require_api_key()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for model in MODELS:
        print(f"Extracting from {VIDEO_PATH.relative_to(ROOT)} with {model}...")
        started = time.perf_counter()
        result = extract(api_key, model, video_b64)
        elapsed = time.perf_counter() - started
        result["model"] = model
        result["elapsed_seconds"] = round(elapsed, 2)

        out_path = OUTPUT_DIR / f"{VIDEO_PATH.stem}_{model}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

        print(f"\n--- {model} ({elapsed:.1f}s) ---")
        print(f"tokens: {format_usage(result['usage'])}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"Saved {out_path.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()

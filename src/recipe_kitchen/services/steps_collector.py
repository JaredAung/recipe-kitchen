"""Extract recipe steps from text with Gemini Flash."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, TypedDict

ROOT = Path(__file__).resolve().parents[3]
MODEL = "gemini-3.5-flash-lite"
GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

StepSource = Literal["audio", "caption", "visual"]
SOURCES: tuple[StepSource, ...] = ("audio", "caption", "visual")


class Step(TypedDict):
    order: int
    instruction: str
    evidence: str
    source: StepSource


PROMPT = """Extract cooking steps from this recipe text.

The text comes from the {source} channel of a recipe video.

For each step return:
- order: 1-based sequence number
- instruction: a clear English cooking action
- evidence: a short verbatim quote from the text that supports this step

Rules:
- Only list actual cooking actions, not greetings, dish titles, or sign-offs.
- Keep steps in the order they happen.
- Split distinct actions into separate steps. Do not merge unrelated actions.
- Keep evidence to one short phrase or sentence copied from the text.
- Do not invent steps, details, or quotes that are not in the text.
- If the text is Burmese, still return English instructions; keep evidence in the original language.
- Return JSON only.

Recipe text:
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
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
        }
    },
    "required": ["steps"],
}


def _load_env(path: Path) -> None:
    """Load KEY=VALUE lines from `path` into os.environ if the file exists."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _require_api_key(api_key: str | None) -> str:
    """Return `api_key` or GEMINI_API_KEY from the environment."""
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Set it in .env")
    return key


def _parse_json(raw: str) -> dict:
    """Parse Gemini JSON, stripping markdown fences if present."""
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


def collect_steps(
    text: str,
    source: StepSource,
    *,
    api_key: str | None = None,
) -> list[Step]:
    """Extract cooking steps from recipe text with Gemini and stamp `source` on each item."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}, got {source!r}")

    _load_env(ROOT / ".env")
    recipe_text = text.strip()
    if not recipe_text:
        raise ValueError("Recipe text is empty.")

    payload = {
        "contents": [{"parts": [{"text": PROMPT.format(source=source) + recipe_text}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }
    request = urllib.request.Request(
        GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": _require_api_key(api_key),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    raw = "".join(part.get("text", "") for part in parts).strip()
    if not raw:
        raise RuntimeError(f"Gemini returned no text: {body}")

    extracted = _parse_json(raw).get("steps") or []
    steps: list[Step] = []
    for index, item in enumerate(extracted, start=1):
        instruction = str(item.get("instruction") or "").strip()
        if not instruction:
            continue
        try:
            order = int(item.get("order") or index)
        except TypeError, ValueError:
            order = index
        steps.append(
            {
                "order": order,
                "instruction": instruction,
                "evidence": str(item.get("evidence") or "").strip(),
                "source": source,
            }
        )
    return steps


def main() -> None:
    """Run step extraction on the sample English ElevenLabs transcript."""
    transcript_path = (
        ROOT / "benchmark" / "speech to text" / "transcripts" / "test1_elevenlabs_en.txt"
    )
    print(f"Collecting steps from {transcript_path}...")
    transcript = transcript_path.read_text(encoding="utf-8")
    steps = collect_steps(transcript, source="audio")
    print("\n--- steps ---")
    print(json.dumps(steps, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

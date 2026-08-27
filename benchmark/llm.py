"""Translate the ElevenLabs transcript to English with Gemini Flash-Lite.
Solely to evaluate the accuracy of the translation. 
Gemini Flash-Lite provides good translation accuracy. 
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINT = (
    ROOT / "benchmark" / "speech to text" / "transcripts" / "test1_elevenlabs.txt"
)
TRANSLATION_PATH = CONSTRAINT.with_name(f"{CONSTRAINT.stem}_en.txt")
MODEL = "gemini-3.5-flash-lite"
GENERATE_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)


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


def translate(api_key: str, transcript: str) -> str:
    prompt = (
        "Translate this Burmese recipe transcript into English.\n"
        "Keep every [MM:SS] timestamp on its own line.\n"
        "Do not add titles, notes, or commentary. Output only the translated transcript.\n\n"
        f"{transcript}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
        },
    }
    request = urllib.request.Request(
        GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

    parts = (
        body.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned no text: {body}")
    return text


def main() -> None:
    load_env(ROOT / ".env")
    if not CONSTRAINT.is_file():
        sys.exit(f"Transcript not found: {CONSTRAINT}")

    transcript = CONSTRAINT.read_text(encoding="utf-8").strip()
    if not transcript:
        sys.exit(f"Transcript is empty: {CONSTRAINT}")

    print(f"Translating {CONSTRAINT.relative_to(ROOT)} with {MODEL}...")
    translation = translate(require_api_key(), transcript)

    TRANSLATION_PATH.write_text(translation + "\n", encoding="utf-8")
    print("\n--- english ---")
    print(translation)
    print(f"\nSaved {TRANSLATION_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

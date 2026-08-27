"""Transcribe shared 55 s audio chunks with Google Speech-to-Text."""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audio as stt_audio

ROOT = SCRIPT_DIR.parents[1]
TRANSCRIPT_PATH = SCRIPT_DIR / "transcripts" / f"{stt_audio.VIDEO_PATH.stem}_googleSTT.txt"
LANGUAGE_CODE = "my-MM"
RECOGNIZE_URL = "https://speech.googleapis.com/v1/speech:recognize"


def require_api_key() -> str:
    key = os.environ.get("GOOGLE_SPEECH_TO_TEXT_API_KEY", "").strip()
    if not key:
        sys.exit("GOOGLE_SPEECH_TO_TEXT_API_KEY is missing. Set it in .env")
    return key


def recognize_chunk(api_key: str, pcm: bytes, chunk_index: int) -> str:
    payload = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": stt_audio.SAMPLE_RATE,
            "languageCode": LANGUAGE_CODE,
            "enableAutomaticPunctuation": True,
        },
        "audio": {"content": base64.b64encode(pcm).decode("ascii")},
    }
    url = f"{RECOGNIZE_URL}?{urllib.parse.urlencode({'key': api_key})}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Speech-to-Text HTTP {exc.code}: {detail}") from exc

    lines: list[str] = []
    chunk_time_offset = (chunk_index - 1) * stt_audio.SYNC_LIMIT_SECONDS

    for result in body.get("results", []):
        end_str = result.get("resultEndTime", "0s").rstrip("s")
        end_time = float(end_str) + chunk_time_offset

        for alt in result.get("alternatives", [])[:1]:
            transcript_text = alt.get("transcript", "").strip()
            if not transcript_text:
                continue

            minutes = int(end_time // 60)
            seconds = int(end_time % 60)
            time_tag = f"[{minutes:02d}:{seconds:02d}]"
            lines.append(f"{time_tag} {transcript_text}")

    return "\n".join(lines)


def main() -> None:
    stt_audio.load_env(ROOT / ".env")
    if not stt_audio.VIDEO_PATH.is_file():
        sys.exit(f"Video not found: {stt_audio.VIDEO_PATH}")

    print(f"Extracting audio from {stt_audio.VIDEO_PATH.name} (not saved)")
    pcm = stt_audio.extract_pcm(stt_audio.require_ffmpeg(), stt_audio.VIDEO_PATH)
    api_key = require_api_key()

    parts: list[str] = []
    chunks = stt_audio.pcm_chunks(pcm)
    for index, chunk in enumerate(chunks, start=1):
        print(f"Transcribing chunk {index}/{len(chunks)}...")
        chunk_transcript = recognize_chunk(api_key, chunk, index)
        if chunk_transcript:
            parts.append(chunk_transcript)

    transcript = "\n".join(part for part in parts if part).strip()
    if not transcript:
        sys.exit("No transcript returned.")

    TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_PATH.write_text(transcript + "\n", encoding="utf-8")
    print("\n--- transcript ---")
    print(transcript)
    print(f"\nSaved {TRANSCRIPT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Transcribe shared 55 s audio chunks with ElevenLabs Scribe."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audio as stt_audio

ROOT = SCRIPT_DIR.parents[1]
TRANSCRIPT_PATH = SCRIPT_DIR / "transcripts" / f"{stt_audio.VIDEO_PATH.stem}_elevenlabs.txt"
LANGUAGE_CODE = "mya"
PAUSE_SECONDS = 0.8
RECOGNIZE_URL = "https://api.elevenlabs.io/v1/speech-to-text"


def require_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit("ELEVENLABS_API_KEY is missing. Set it in .env")
    return key


def multipart_body(
    fields: dict[str, str],
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> tuple[bytes, str]:
    boundary = "----STTBoundary" + os.urandom(8).hex()
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def time_tag(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"[{total // 60:02d}:{total % 60:02d}]"


def format_transcript(body: dict, time_offset: float = 0) -> str:
    words = [
        word
        for word in body.get("words", [])
        if word.get("type") in {"word", "spacing"} and word.get("text")
    ]
    if not words:
        return (body.get("text") or "").strip()

    lines: list[str] = []
    current: list[str] = []
    line_start: float | None = None
    prev_end: float | None = None

    def flush() -> None:
        nonlocal current, line_start
        text = "".join(current).strip()
        if text and line_start is not None:
            lines.append(f"{time_tag(line_start + time_offset)} {text}")
        current = []
        line_start = None

    for word in words:
        start = float(word.get("start") or prev_end or 0)
        end = float(word.get("end") or start)
        if (
            word.get("type") == "word"
            and prev_end is not None
            and start - prev_end >= PAUSE_SECONDS
        ):
            flush()
        if line_start is None and word.get("type") == "word":
            line_start = start
        current.append(word["text"])
        prev_end = end

    flush()
    return "\n".join(lines)


def recognize(api_key: str, wav_bytes: bytes) -> dict:
    body, content_type = multipart_body(
        {
            "model_id": "scribe_v2",
            "language_code": LANGUAGE_CODE,
            "timestamps_granularity": "word",
        },
        "audio.wav",
        wav_bytes,
        "audio/wav",
    )
    request = urllib.request.Request(
        RECOGNIZE_URL,
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs HTTP {exc.code}: {detail}") from exc


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
        print(f"Transcribing chunk {index}/{len(chunks)} with ElevenLabs Scribe v2...")
        offset = (index - 1) * stt_audio.SYNC_LIMIT_SECONDS
        body = recognize(api_key, stt_audio.pcm_to_wav(chunk))
        chunk_transcript = format_transcript(body, offset).strip()
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

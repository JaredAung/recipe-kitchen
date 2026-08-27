"""Transcribe Burmese narration with ElevenLabs Scribe."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from recipe_kitchen.services.audio_extractor import extract_pcm, pcm_to_wav

ROOT = Path(__file__).resolve().parents[3]
LANGUAGE_CODE = "mya"
PAUSE_SECONDS = 0.8
RECOGNIZE_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL_ID = "scribe_v2"


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
    """Return `api_key` or ELEVENLABS_API_KEY from the environment."""
    key = (api_key or os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing. Set it in .env")
    return key


def _multipart_body(
    fields: dict[str, str],
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> tuple[bytes, str]:
    """Build a multipart/form-data body and its Content-Type header."""
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


def _time_tag(seconds: float) -> str:
    """Format seconds as a `[MM:SS]` timestamp."""
    total = max(0, int(seconds))
    return f"[{total // 60:02d}:{total % 60:02d}]"


def format_transcript(body: dict) -> str:
    """Turn an ElevenLabs word list into timestamped transcript lines."""
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
        """Append the current line to `lines` and reset the buffer."""
        nonlocal current, line_start
        text = "".join(current).strip()
        if text and line_start is not None:
            lines.append(f"{_time_tag(line_start)} {text}")
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
    """Send WAV audio to ElevenLabs Scribe and return the JSON response."""
    body, content_type = _multipart_body(
        {
            "model_id": MODEL_ID,
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


def transcribe_wav(wav_bytes: bytes, *, api_key: str | None = None) -> str:
    """Return a timestamped Burmese transcript from 16 kHz mono WAV bytes."""
    _load_env(ROOT / ".env")
    body = recognize(_require_api_key(api_key), wav_bytes)
    transcript = format_transcript(body).strip()
    if not transcript:
        raise RuntimeError("No transcript returned.")
    return transcript


def transcribe_burmese(video_path: str | Path, *, api_key: str | None = None) -> str:
    """Extract audio from a video and return a timestamped Burmese transcript."""
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    return transcribe_wav(pcm_to_wav(extract_pcm(path)), api_key=api_key)


def main() -> None:
    """Transcribe the sample video at tests/test1.mp4 and print the result."""
    video_path = ROOT / "tests" / "test1.mp4"
    print(f"Transcribing {video_path}...")
    transcript = transcribe_burmese(video_path)
    print("\n--- transcript ---")
    print(transcript)


if __name__ == "__main__":
    main()

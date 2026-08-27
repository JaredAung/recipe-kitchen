"""Extract 16 kHz mono PCM from a video and wrap it as WAV."""

from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path

SAMPLE_RATE = 16000


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path, or raise if it is not installed."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found. Install it first, e.g. `brew install ffmpeg`.")
    return ffmpeg


def extract_pcm(video_path: str | Path, ffmpeg: str | None = None) -> bytes:
    """Extract 16 kHz mono signed-16-bit PCM from a video file."""
    path = Path(video_path)
    ffmpeg = ffmpeg or _require_ffmpeg()
    result = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-f",
            "s16le",
            "pipe:1",
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {path.name}:\n{result.stderr.decode().strip()}"
        )
    return result.stdout


def pcm_to_wav(pcm: bytes) -> bytes:
    """Wrap raw PCM bytes in a WAV header for speech-to-text APIs."""
    data_size = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        SAMPLE_RATE,
        SAMPLE_RATE * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + pcm

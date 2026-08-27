"""Shared 16 kHz mono extract and 55 s chunks for the STT comparison."""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SAMPLE_RATE = 16000
SYNC_LIMIT_SECONDS = 55
BYTES_PER_SECOND = SAMPLE_RATE * 2  # 16-bit mono PCM
VIDEO_PATH = Path(__file__).resolve().parents[2] / "testing-material" / "test1.mp4"


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found. Install it first, e.g. `brew install ffmpeg`.")
    return ffmpeg


def extract_pcm(ffmpeg: str, video_path: Path) -> bytes:
    result = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-i",
            str(video_path),
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
            f"ffmpeg failed for {video_path.name}:\n{result.stderr.decode().strip()}"
        )
    return result.stdout


def pcm_chunks(pcm: bytes) -> list[bytes]:
    chunk_bytes = SYNC_LIMIT_SECONDS * BYTES_PER_SECOND
    return [
        pcm[i : i + chunk_bytes]
        for i in range(0, len(pcm), chunk_bytes)
        if pcm[i : i + chunk_bytes]
    ]


def pcm_to_wav(pcm: bytes) -> bytes:
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

"""Silero VAD: detect speech in test1, test5, and test6.

Run from the repo root:

    uv run --with silero-vad python "benchmark/speech-detech/Silero VAD.py"
"""

from __future__ import annotations

import json
import sys
from array import array
from pathlib import Path

from recipe_kitchen.services.audio_extractor import SAMPLE_RATE, extract_pcm
from silero_vad import get_speech_timestamps, load_silero_vad

ROOT = Path(__file__).resolve().parents[2]
VIDEOS = tuple(ROOT / "testing-material" / name for name in ("test1.mp4", "test5.mp4", "test6.mp4"))
OUTPUT_PATH = Path(__file__).resolve().parent / "results" / "silero_vad.json"
MIN_SPEECH_SECONDS = 1.0


def pcm_to_float_tensor(pcm: bytes):
    """Convert 16-bit mono PCM to a 1-D float32 tensor in [-1, 1]."""
    import torch

    if not pcm:
        return torch.zeros(0, dtype=torch.float32)
    samples = array("h")
    samples.frombytes(pcm)
    return torch.tensor(samples, dtype=torch.float32) / 32768.0


def speech_seconds(segments: list[dict[str, float]]) -> float:
    """Total duration of VAD speech segments."""
    return sum(max(0.0, segment["end"] - segment["start"]) for segment in segments)


def detect_speech(model, video_path: Path) -> dict:
    """Extract 16 kHz audio and return Silero speech timestamps."""
    pcm = extract_pcm(video_path)
    duration = len(pcm) / (SAMPLE_RATE * 2)
    wav = pcm_to_float_tensor(pcm)
    segments = get_speech_timestamps(
        wav,
        model,
        sampling_rate=SAMPLE_RATE,
        return_seconds=True,
    )
    spoken = round(speech_seconds(segments), 2)
    return {
        "video": video_path.name,
        "duration_seconds": round(duration, 2),
        "speech_seconds": spoken,
        "speech_ratio": round(spoken / duration, 3) if duration else 0.0,
        "segments": [
            {"start": round(float(item["start"]), 2), "end": round(float(item["end"]), 2)}
            for item in segments
        ],
        "has_speech": spoken >= MIN_SPEECH_SECONDS,
    }


def main() -> None:
    missing = [path for path in VIDEOS if not path.is_file()]
    if missing:
        sys.exit("Video not found:\n" + "\n".join(str(path) for path in missing))

    print("Loading Silero VAD...")
    model = load_silero_vad()
    results = [detect_speech(model, path) for path in VIDEOS]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")

    print(f"has_speech if speech_seconds >= {MIN_SPEECH_SECONDS:.1f}s\n")
    for item in results:
        flag = "SPEECH" if item["has_speech"] else "NO SPEECH"
        print(
            f"{item['video']:10} {flag:10}  "
            f"duration={item['duration_seconds']:.1f}s  "
            f"speech={item['speech_seconds']:.1f}s  "
            f"segments={len(item['segments'])}"
        )
        for segment in item["segments"][:8]:
            print(f"           [{segment['start']:.2f}–{segment['end']:.2f}]")
        if len(item["segments"]) > 8:
            print(f"           … {len(item['segments']) - 8} more")
    print(f"\nSaved {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

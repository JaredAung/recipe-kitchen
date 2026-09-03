"""Silero VAD: decide whether a 16 kHz mono PCM buffer contains speech."""

from __future__ import annotations

import logging
from array import array
from functools import lru_cache

from recipe_kitchen.services.audio_extractor import SAMPLE_RATE

MIN_SPEECH_SECONDS = 1.0

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _vad_model():
    """Load Silero VAD once per process."""
    from silero_vad import load_silero_vad

    return load_silero_vad()


def pcm_to_float_tensor(pcm: bytes):
    """Convert 16-bit mono PCM to a 1-D float32 tensor in [-1, 1]."""
    import torch

    if not pcm:
        return torch.zeros(0, dtype=torch.float32)
    samples = array("h")
    samples.frombytes(pcm)
    return torch.tensor(samples, dtype=torch.float32) / 32768.0


def speech_seconds(pcm: bytes) -> float:
    """Total duration of Silero speech segments in `pcm`."""
    from silero_vad import get_speech_timestamps

    wav = pcm_to_float_tensor(pcm)
    if wav.numel() == 0:
        return 0.0
    segments = get_speech_timestamps(
        wav,
        _vad_model(),
        sampling_rate=SAMPLE_RATE,
        return_seconds=True,
    )
    return sum(max(0.0, float(item["end"]) - float(item["start"])) for item in segments)


def has_speech(pcm: bytes, *, min_seconds: float = MIN_SPEECH_SECONDS) -> bool:
    """Return True when Silero finds at least `min_seconds` of speech."""
    spoken = speech_seconds(pcm)
    found = spoken >= min_seconds
    logger.info(
        "VAD speech=%.2fs threshold=%.1fs has_speech=%s",
        spoken,
        min_seconds,
        found,
    )
    return found

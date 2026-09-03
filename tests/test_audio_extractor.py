import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from recipe_kitchen.services.audio_extractor import mute_video


def test_mute_video_drops_audio_and_copies_video(tmp_path: Path) -> None:
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"with-audio")
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess[bytes]:
        seen.append(cmd)
        Path(cmd[-1]).write_bytes(b"silent-mp4")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    with (
        patch("recipe_kitchen.services.audio_extractor._require_ffmpeg", return_value="ffmpeg"),
        patch("recipe_kitchen.services.audio_extractor.subprocess.run", side_effect=fake_run),
    ):
        muted = mute_video(src)

    assert muted == b"silent-mp4"
    cmd = seen[0]
    assert cmd[:6] == ["ffmpeg", "-nostdin", "-i", str(src), "-an", "-c:v"]
    assert cmd[6] == "copy"
    assert not Path(cmd[-1]).exists()


def test_mute_video_raises_when_ffmpeg_fails(tmp_path: Path) -> None:
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"bad")

    failed = subprocess.CompletedProcess(["ffmpeg"], 1, b"", b"no decoder")
    with (
        patch("recipe_kitchen.services.audio_extractor._require_ffmpeg", return_value="ffmpeg"),
        patch("recipe_kitchen.services.audio_extractor.subprocess.run", return_value=failed),
        pytest.raises(RuntimeError, match="ffmpeg mute failed"),
    ):
        mute_video(src)

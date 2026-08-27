from recipe_kitchen.services.ingestion.subtitle_text import _cue_text


def test_cue_text_keeps_timestamps_and_spoken_lines() -> None:
    raw = """WEBVTT

1
00:00:01.000 --> 00:00:03.000
Hello <b>world</b>

2
00:00:04.000 --> 00:00:05.000
Add the fish
"""
    assert _cue_text(raw) == (
        "00:00:01.000 --> 00:00:03.000\nHello world\n00:00:04.000 --> 00:00:05.000\nAdd the fish"
    )

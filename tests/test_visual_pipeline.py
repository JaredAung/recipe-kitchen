from unittest.mock import MagicMock, patch

from recipe_kitchen.services.visual_pipeline import (
    _clamp_confidence,
    _GeminiVisual,
    _to_ingredients,
    extract_visual_channel,
)


def test_visual_schema_clears_overlay_copied_into_amount() -> None:
    parsed = _GeminiVisual.model_validate(
        {
            "confidence": 0.86,
            "ingredients": [
                {"name": "Onion", "amount": "Onion", "evidence": "Onion", "confidence": 0.95},
                {"name": "oil", "amount": "2 tbsp", "evidence": "oil poured", "confidence": 0.8},
            ],
            "steps": [
                {"order": 1, "instruction": "Fry", "evidence": "pan", "confidence": 0.7},
            ],
        }
    )

    ingredients = _to_ingredients(parsed.ingredients)
    assert ingredients[0].amount == ""
    assert ingredients[0].source == "visual"
    assert ingredients[0].confidence == 0.95
    assert ingredients[1].amount == "2 tbsp"
    assert parsed.confidence == 0.86


def test_visual_schema_clamps_percent_confidence_and_fills_overall() -> None:
    parsed = _GeminiVisual.model_validate(
        {
            "ingredients": [
                {"name": "egg", "amount": "", "evidence": "cracked", "confidence": 90},
            ],
            "steps": [
                {"order": 1, "instruction": "Crack eggs", "evidence": "bowl", "confidence": 80},
            ],
        }
    )

    assert parsed.ingredients[0].confidence == 0.9
    assert parsed.steps[0].confidence == 0.8
    assert parsed.confidence == 0.85


def test_clamp_confidence_rejects_blank() -> None:
    assert _clamp_confidence(None) is None
    assert _clamp_confidence("") is None
    assert _clamp_confidence(1.2) == 1.0
    assert _clamp_confidence(90) == 0.9
    assert _clamp_confidence(0.4) == 0.4


def test_extract_visual_channel_uploads_muted_video(tmp_path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"with-audio")
    parsed = _GeminiVisual.model_validate(
        {
            "confidence": 0.9,
            "ingredients": [
                {"name": "oil", "amount": "", "evidence": "poured", "confidence": 0.9},
            ],
            "steps": [
                {"order": 1, "instruction": "Heat oil", "evidence": "pan", "confidence": 0.8},
            ],
        }
    )
    response = MagicMock()
    response.parsed = parsed
    response.usage_metadata = None
    response.text = ""
    client = MagicMock()
    client.models.generate_content.return_value = response

    with (
        patch("recipe_kitchen.services.visual_pipeline.mute_video", return_value=b"silent") as mute,
        patch("recipe_kitchen.services.visual_pipeline.genai.Client", return_value=client),
        patch("recipe_kitchen.services.visual_pipeline.require_api_key", return_value="k"),
        patch("recipe_kitchen.services.visual_pipeline.load_env"),
        patch("recipe_kitchen.services.visual_pipeline.record_token_usage"),
    ):
        extract_visual_channel(video)

    mute.assert_called_once_with(video)
    contents = client.models.generate_content.call_args.kwargs["contents"]
    assert contents[0].inline_data.data == b"silent"
    assert contents[0].inline_data.mime_type == "video/mp4"

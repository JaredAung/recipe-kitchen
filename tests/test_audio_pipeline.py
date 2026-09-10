from pathlib import Path
from unittest.mock import patch

from recipe_kitchen.schemas.extract import AudioExtract
from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.audio_pipeline import extract_audio_channel

PCM = "recipe_kitchen.services.audio_pipeline.extract_pcm"
HAS_SPEECH = "recipe_kitchen.services.audio_pipeline.has_speech"
TRANSCRIBE = "recipe_kitchen.services.audio_pipeline.transcribe_wav"
COLLECT_INGREDIENTS = "recipe_kitchen.services.audio_pipeline.collect_ingredients"
COLLECT_STEPS = "recipe_kitchen.services.audio_pipeline.collect_steps"
COLLECT_BILINGUAL = "recipe_kitchen.services.audio_pipeline.collect_bilingual"
IS_BURMESE = "recipe_kitchen.services.audio_pipeline.is_burmese"
TRANSLATE = "recipe_kitchen.services.audio_pipeline.translate_to_english"
PCM_TO_WAV = "recipe_kitchen.services.audio_pipeline.pcm_to_wav"


def test_extract_audio_skips_stt_when_vad_finds_no_speech(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    with (
        patch(PCM, return_value=b"\x00\x00"),
        patch(HAS_SPEECH, return_value=False) as vad,
        patch(TRANSCRIBE) as transcribe,
        patch(COLLECT_INGREDIENTS) as collect_ingredients,
        patch(COLLECT_STEPS) as collect_steps,
        patch(COLLECT_BILINGUAL) as bilingual,
    ):
        result = extract_audio_channel(video)

    assert result == AudioExtract(transcript_en="", ingredients=[], steps=[])
    vad.assert_called_once()
    transcribe.assert_not_called()
    collect_ingredients.assert_not_called()
    collect_steps.assert_not_called()
    bilingual.assert_not_called()


def test_extract_audio_transcribes_when_vad_finds_speech(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    oil = {"name": "oil", "amount": "1 tbsp", "evidence": "heat oil", "source": "audio"}
    heat = {"order": 1, "instruction": "Heat the oil", "evidence": "heat", "source": "audio"}
    with (
        patch(PCM, return_value=b"\x00\x00"),
        patch(HAS_SPEECH, return_value=True),
        patch(TRANSCRIBE, return_value="Heat the oil") as transcribe,
        patch(COLLECT_INGREDIENTS, return_value=[oil]) as collect_ingredients,
        patch(COLLECT_STEPS, return_value=[heat]) as collect_steps,
        patch(PCM_TO_WAV, return_value=b"wav"),
        patch(IS_BURMESE, return_value=False),
        patch(TRANSLATE) as translate,
        patch(COLLECT_BILINGUAL) as bilingual,
    ):
        result = extract_audio_channel(video)

    transcribe.assert_called_once()
    collect_ingredients.assert_called_once_with("Heat the oil", source="audio")
    collect_steps.assert_called_once_with("Heat the oil", source="audio")
    translate.assert_not_called()
    bilingual.assert_not_called()
    assert result.transcript_en == "Heat the oil"
    assert result.transcript_my is None
    assert result.ingredients == [Ingredient.model_validate(oil)]
    assert result.steps == [Step.model_validate(heat)]


def test_extract_audio_collects_burmese_in_parallel(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    spoken = "ဆီထည့်ပြီး ကြော်ပါ"
    oil = Ingredient(name="oil", amount="1 tbsp", evidence="ဆီထည့်ပြီး", source="audio")
    fry = Step(order=1, instruction="Fry", evidence="ကြော်ပါ", source="audio")
    with (
        patch(PCM, return_value=b"\x00\x00"),
        patch(HAS_SPEECH, return_value=True),
        patch(TRANSCRIBE, return_value=spoken),
        patch(COLLECT_INGREDIENTS) as collect_ingredients,
        patch(COLLECT_STEPS) as collect_steps,
        patch(COLLECT_BILINGUAL, return_value=([oil], [fry])) as bilingual,
        patch(PCM_TO_WAV, return_value=b"wav"),
        patch(IS_BURMESE, return_value=True),
        patch(TRANSLATE, return_value="Add oil and fry") as translate,
    ):
        result = extract_audio_channel(video)

    collect_ingredients.assert_not_called()
    collect_steps.assert_not_called()
    translate.assert_called_once_with(spoken)
    bilingual.assert_called_once_with(spoken, "Add oil and fry", source="audio")
    assert result.transcript_my == spoken
    assert result.transcript_en == "Add oil and fry"
    assert result.ingredients == [oil]
    assert result.steps == [fry]

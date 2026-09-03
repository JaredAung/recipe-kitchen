from pathlib import Path
from unittest.mock import patch

import pytest

from recipe_kitchen.schemas.extract import (
    AudioExtract,
    CaptionExtract,
    RecipeMetadata,
    Sufficiency,
)
from recipe_kitchen.schemas.recipe import Ingredient, Step, VisualExtract
from recipe_kitchen.services.recipe_pipeline import run_recipe_pipeline

CAPTION_FISH = Ingredient(
    name="fish",
    amount="1",
    evidence="whole fish",
    source="caption",
)
CAPTION_FRY = Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")
SUBTITLE_SALT = Ingredient(
    name="salt",
    amount="1 tsp",
    evidence="add salt",
    source="caption",
)
SUBTITLE_SEASON = Step(order=2, instruction="Season with salt", evidence="salt", source="caption")
AUDIO_OIL = Ingredient(name="oil", amount="2 tbsp", evidence="heat oil", source="audio")
AUDIO_HEAT = Step(order=1, instruction="Heat the oil", evidence="heat", source="audio")
VISUAL_PEPPER = Ingredient(name="capsicum", amount="", evidence="Capsicum", source="visual")
VISUAL_ADD = Step(order=1, instruction="Add capsicum", evidence="Capsicum", source="visual")

EXTRACT_CAPTION = "recipe_kitchen.graph.nodes.extract_caption_channel"
IS_SUFFICIENT = "recipe_kitchen.graph.nodes.is_sufficient"
EXTRACT_AUDIO = "recipe_kitchen.graph.nodes.extract_audio_channel"
EXTRACT_VISUAL = "recipe_kitchen.graph.nodes.extract_visual_channel"
FETCH_VIDEO = "recipe_kitchen.graph.nodes.fetch_stored_video"
EXTRACT_METADATA = "recipe_kitchen.graph.nodes.extract_recipe_metadata"
ADD_RECIPE = "recipe_kitchen.graph.nodes.add_recipe"
METADATA = RecipeMetadata(
    title="Fried Fish",
    cuisine="chinese",
    description="Pan-fried fish with a simple seasoning.",
    tags=["fish", "fried"],
    total_time_minutes=25,
)


def _caption_extract(
    *,
    ingredients: list[Ingredient],
    steps: list[Step],
    text: str,
) -> CaptionExtract:
    return CaptionExtract(
        ingredients=ingredients,
        steps=steps,
        source_text=text,
        text_en=text,
    )


@pytest.fixture(autouse=True)
def _stub_metadata() -> object:
    with patch(EXTRACT_METADATA, return_value=METADATA):
        yield


def test_pipeline_skips_marketing_caption_and_runs_audio() -> None:
    caption = "Maggi Omlette 🥪"
    with (
        patch(
            "recipe_kitchen.services.caption_pipeline.collect_ingredients",
        ) as collect_ing,
        patch("recipe_kitchen.services.caption_pipeline.collect_steps") as collect_steps,
        patch(
            IS_SUFFICIENT,
            side_effect=[
                Sufficiency(sufficient=False, reason="Need at least one ingredient and one step."),
                Sufficiency(sufficient=True, reason="audio completes it"),
            ],
        ),
        patch(
            EXTRACT_AUDIO,
            return_value=AudioExtract(
                transcript_en="Heat oil and fry the fish",
                ingredients=[AUDIO_OIL],
                steps=[AUDIO_HEAT],
            ),
        ) as extract_audio,
        patch(EXTRACT_VISUAL) as extract_visual,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "audio"
    assert result.ingredients == [AUDIO_OIL]
    collect_ing.assert_not_called()
    collect_steps.assert_not_called()
    extract_audio.assert_called_once()
    extract_visual.assert_not_called()


def test_pipeline_stops_after_sufficient_caption() -> None:
    caption = "Fry a whole fish"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text=caption,
            ),
        ) as extract_caption,
        patch(
            IS_SUFFICIENT,
            return_value=Sufficiency(sufficient=True, reason="complete"),
        ),
        patch(EXTRACT_AUDIO) as extract_audio,
        patch(EXTRACT_VISUAL) as extract_visual,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            subtitle_text="add salt",
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "caption"
    assert result.sufficient is True
    assert result.ingredients == [CAPTION_FISH]
    extract_caption.assert_called_once_with(caption, source="caption")
    extract_audio.assert_not_called()
    extract_visual.assert_not_called()


def test_pipeline_adds_subtitles_when_caption_is_not_enough() -> None:
    caption = "a fish dish"
    subtitles = "add salt and fry"
    extracts = [
        _caption_extract(ingredients=[CAPTION_FISH], steps=[CAPTION_FRY], text=caption),
        _caption_extract(ingredients=[SUBTITLE_SALT], steps=[SUBTITLE_SEASON], text=subtitles),
    ]
    judgments = [
        Sufficiency(sufficient=False, reason="too thin"),
        Sufficiency(sufficient=True, reason="together enough"),
    ]
    with (
        patch(EXTRACT_CAPTION, side_effect=extracts) as extract_caption,
        patch(IS_SUFFICIENT, side_effect=judgments),
        patch(EXTRACT_AUDIO) as extract_audio,
        patch(EXTRACT_VISUAL) as extract_visual,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            subtitle_text=subtitles,
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "subtitle"
    assert result.ingredients == [CAPTION_FISH, SUBTITLE_SALT]
    assert [call.args[0] for call in extract_caption.call_args_list] == [caption, subtitles]
    extract_audio.assert_not_called()
    extract_visual.assert_not_called()


def test_pipeline_runs_audio_when_text_is_not_enough() -> None:
    caption = "a fish dish"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text=caption,
            ),
        ),
        patch(
            IS_SUFFICIENT,
            side_effect=[
                Sufficiency(sufficient=False, reason="caption too thin"),
                Sufficiency(sufficient=True, reason="audio completes it"),
            ],
        ),
        patch(
            EXTRACT_AUDIO,
            return_value=AudioExtract(
                transcript_en="Heat oil and fry the fish",
                ingredients=[AUDIO_OIL],
                steps=[AUDIO_HEAT],
            ),
        ) as extract_audio,
        patch(EXTRACT_VISUAL) as extract_visual,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            subtitle_text="",
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "audio"
    assert result.ingredients == [CAPTION_FISH, AUDIO_OIL]
    extract_audio.assert_called_once()
    extract_visual.assert_not_called()


def test_pipeline_runs_visual_when_audio_is_not_enough() -> None:
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text="x",
            ),
        ),
        patch(
            IS_SUFFICIENT,
            side_effect=[
                Sufficiency(sufficient=False, reason="caption too thin"),
                Sufficiency(sufficient=False, reason="audio too thin"),
                Sufficiency(sufficient=True, reason="visual completes it"),
            ],
        ),
        patch(
            EXTRACT_AUDIO,
            return_value=AudioExtract(
                transcript_en="Heat oil",
                ingredients=[AUDIO_OIL],
                steps=[AUDIO_HEAT],
            ),
        ) as extract_audio,
        patch(
            EXTRACT_VISUAL,
            return_value=VisualExtract(
                ingredients=[VISUAL_PEPPER],
                steps=[VISUAL_ADD],
                transcript_en="Capsicum",
            ),
        ) as extract_visual,
    ):
        result = run_recipe_pipeline(
            caption="thin caption",
            subtitle_text="",
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "visual"
    assert result.ingredients == [CAPTION_FISH, AUDIO_OIL, VISUAL_PEPPER]
    extract_audio.assert_called_once()
    extract_visual.assert_called_once()


def test_pipeline_ends_without_video_when_text_is_not_enough() -> None:
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text="thin caption",
            ),
        ),
        patch(
            IS_SUFFICIENT,
            return_value=Sufficiency(sufficient=False, reason="too thin"),
        ),
        patch(EXTRACT_AUDIO) as extract_audio,
        patch(EXTRACT_VISUAL) as extract_visual,
    ):
        result = run_recipe_pipeline(caption="thin caption", subtitle_text="", save=False)

    assert result.stopped_after == "caption"
    assert result.sufficient is False
    extract_audio.assert_not_called()
    extract_visual.assert_not_called()


def test_pipeline_does_not_enrich_when_insufficient() -> None:
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text="thin caption",
            ),
        ),
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=False, reason="too thin")),
        patch(EXTRACT_METADATA) as extract_metadata,
    ):
        result = run_recipe_pipeline(caption="thin caption", subtitle_text="", save=False)

    extract_metadata.assert_not_called()
    assert result.title == ""
    assert result.cuisine == ""
    assert result.description == ""
    assert result.tags == []
    assert result.total_time_minutes is None
    assert result.validation_confidence is None


def test_pipeline_merges_duplicate_ingredient_from_audio() -> None:
    audio_fish = Ingredient(
        name="fish",
        amount="1",
        evidence="washed fish",
        source="audio",
    )
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text="a fish dish",
            ),
        ),
        patch(
            IS_SUFFICIENT,
            side_effect=[
                Sufficiency(sufficient=False, reason="caption too thin"),
                Sufficiency(sufficient=True, reason="audio completes it"),
            ],
        ),
        patch(
            EXTRACT_AUDIO,
            return_value=AudioExtract(
                transcript_en="Wash the fish and heat oil",
                ingredients=[audio_fish, AUDIO_OIL],
                steps=[AUDIO_HEAT],
            ),
        ),
        patch(EXTRACT_VISUAL),
    ):
        result = run_recipe_pipeline(
            caption="a fish dish",
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.ingredients == [audio_fish, AUDIO_OIL]
    assert result.steps == [
        CAPTION_FRY,
        AUDIO_HEAT.model_copy(update={"order": 2}),
    ]


def test_pipeline_requires_a_channel() -> None:
    with pytest.raises(RuntimeError, match="without running a channel"):
        run_recipe_pipeline(caption="", subtitle_text="", save=False)


def test_pipeline_does_not_fetch_video_when_caption_is_enough() -> None:
    caption = "Fry a whole fish"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text=caption,
            ),
        ),
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=True, reason="complete")),
        patch(FETCH_VIDEO) as fetch_video,
        patch(EXTRACT_AUDIO) as extract_audio,
        patch(EXTRACT_VISUAL) as extract_visual,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            video_storage_path="123/video.mp4",
            save=False,
        )

    assert result.stopped_after == "caption"
    fetch_video.assert_not_called()
    extract_audio.assert_not_called()
    extract_visual.assert_not_called()


def test_pipeline_fetches_stored_video_in_audio_and_reuses_it_for_visual() -> None:
    seen: list[tuple[str, Path, bool]] = []

    def fake_audio(path: Path) -> AudioExtract:
        seen.append(("audio", path, path.is_file()))
        return AudioExtract(
            transcript_en="Heat oil",
            ingredients=[AUDIO_OIL],
            steps=[AUDIO_HEAT],
        )

    def fake_visual(path: Path) -> VisualExtract:
        seen.append(("visual", path, path.is_file()))
        return VisualExtract(
            ingredients=[VISUAL_PEPPER],
            steps=[VISUAL_ADD],
            transcript_en="Capsicum",
        )

    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text="x",
            ),
        ),
        patch(
            IS_SUFFICIENT,
            side_effect=[
                Sufficiency(sufficient=False, reason="caption too thin"),
                Sufficiency(sufficient=False, reason="audio too thin"),
                Sufficiency(sufficient=True, reason="visual completes it"),
            ],
        ),
        patch(FETCH_VIDEO, return_value=b"fake-mp4") as fetch_video,
        patch(EXTRACT_AUDIO, side_effect=fake_audio),
        patch(EXTRACT_VISUAL, side_effect=fake_visual),
    ):
        result = run_recipe_pipeline(
            caption="thin caption",
            video_storage_path="123/video.mp4",
            save=False,
        )

    assert result.stopped_after == "visual"
    fetch_video.assert_called_once_with("123/video.mp4")
    assert [name for name, _path, _exists in seen] == ["audio", "visual"]
    assert seen[0][1] == seen[1][1]
    assert seen[0][2] is True
    assert seen[1][2] is True
    assert not seen[0][1].exists()


def test_pipeline_skips_stt_overwrite_when_audio_has_no_speech() -> None:
    caption = "thin caption"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text=caption,
            ),
        ),
        patch(
            IS_SUFFICIENT,
            side_effect=[
                Sufficiency(sufficient=False, reason="caption too thin"),
                Sufficiency(sufficient=True, reason="visual completes it"),
            ],
        ) as is_sufficient,
        patch(
            EXTRACT_AUDIO,
            return_value=AudioExtract(transcript_en="", ingredients=[], steps=[]),
        ),
        patch(
            EXTRACT_VISUAL,
            return_value=VisualExtract(
                ingredients=[VISUAL_PEPPER],
                steps=[VISUAL_ADD],
                transcript_en="Capsicum",
            ),
        ),
    ):
        result = run_recipe_pipeline(
            caption=caption,
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "visual"
    assert result.transcript_en == caption
    assert result.ingredients == [CAPTION_FISH, VISUAL_PEPPER]
    assert is_sufficient.call_count == 2


def test_pipeline_skips_audio_judge_when_silent_and_no_caption() -> None:
    with (
        patch(EXTRACT_CAPTION) as extract_caption,
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=True, reason="visual")) as judge,
        patch(
            EXTRACT_AUDIO,
            return_value=AudioExtract(transcript_en="", ingredients=[], steps=[]),
        ),
        patch(
            EXTRACT_VISUAL,
            return_value=VisualExtract(
                ingredients=[VISUAL_PEPPER],
                steps=[VISUAL_ADD],
                transcript_en="Capsicum",
            ),
        ),
    ):
        result = run_recipe_pipeline(caption="", video_path=Path("video.mp4"), save=False)

    extract_caption.assert_not_called()
    assert result.stopped_after == "visual"
    assert judge.call_count == 1
    assert result.ingredients == [VISUAL_PEPPER]
    assert result.title == "Fried Fish"


def test_pipeline_enriches_when_sufficient() -> None:
    caption = "Fry a whole fish"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text=caption,
            ),
        ),
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=True, reason="complete")),
        patch(EXTRACT_AUDIO) as extract_audio,
        patch(EXTRACT_METADATA, return_value=METADATA) as extract_metadata,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            video_path=Path("video.mp4"),
            save=False,
        )

    assert result.stopped_after == "caption"
    assert result.sufficient is True
    assert result.title == "Fried Fish"
    assert result.cuisine == "chinese"
    assert result.description == "Pan-fried fish with a simple seasoning."
    assert result.tags == ["fish", "fried"]
    assert result.total_time_minutes == 25
    assert result.validation_confidence == 1.0
    extract_metadata.assert_called_once()
    extract_audio.assert_not_called()


def test_pipeline_flags_issues_without_blocking() -> None:
    invented = Ingredient(
        name="fish",
        amount="1",
        evidence="totally invented quote xyz",
        source="caption",
    )
    spices = Ingredient(name="spices", amount="", evidence="add spices", source="caption")
    fry = Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")
    caption = "Fry the fish and add spices"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[invented, spices],
                steps=[fry],
                text=caption,
            ),
        ),
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=True, reason="complete")),
    ):
        result = run_recipe_pipeline(caption=caption, save=False)

    codes = {issue.code for issue in result.validation_issues}
    assert result.sufficient is True
    assert result.title == "Fried Fish"
    assert "ungrounded_evidence" in codes
    assert "generic_name" in codes
    assert result.validation_confidence is not None
    assert result.validation_confidence < 1.0


def test_pipeline_saves_after_enrich() -> None:
    caption = "Fry a whole fish"
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text=caption,
            ),
        ),
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=True, reason="complete")),
        patch(ADD_RECIPE, return_value={"id": "rec-1"}) as add_recipe,
    ):
        result = run_recipe_pipeline(
            caption=caption,
            original_filename="fish.mp4",
            source_url="https://example.com/reel",
            save=True,
        )

    assert result.id == "rec-1"
    add_recipe.assert_called_once()
    created = add_recipe.call_args.args[0]
    assert created.title == "Fried Fish"
    assert created.cuisine == "chinese"
    assert created.description == "Pan-fried fish with a simple seasoning."
    assert created.tags == ["fish", "fried"]
    assert created.total_time_minutes == 25
    assert created.original_filename == "fish.mp4"
    assert created.source_url == "https://example.com/reel"
    assert created.extraction_meta["sufficient"] is True


def test_pipeline_does_not_save_when_insufficient() -> None:
    with (
        patch(
            EXTRACT_CAPTION,
            return_value=_caption_extract(
                ingredients=[CAPTION_FISH],
                steps=[CAPTION_FRY],
                text="thin caption",
            ),
        ),
        patch(IS_SUFFICIENT, return_value=Sufficiency(sufficient=False, reason="too thin")),
        patch(ADD_RECIPE) as add_recipe,
    ):
        result = run_recipe_pipeline(caption="thin caption", save=True)

    add_recipe.assert_not_called()
    assert result.id == ""
    assert result.sufficient is False

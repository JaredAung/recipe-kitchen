from unittest.mock import patch

from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.caption_pipeline import extract_caption_channel


def test_extract_caption_channel_skips_empty_text() -> None:
    with (
        patch("recipe_kitchen.services.caption_pipeline.collect_ingredients") as collect_ing,
        patch("recipe_kitchen.services.caption_pipeline.collect_steps") as collect_steps,
    ):
        extracted = extract_caption_channel("  ", source="caption")

    assert extracted.ingredients == []
    assert extracted.steps == []
    collect_ing.assert_not_called()
    collect_steps.assert_not_called()


def test_extract_caption_channel_stamps_caption_source() -> None:
    with (
        patch(
            "recipe_kitchen.services.caption_pipeline.collect_ingredients",
            return_value=[
                {
                    "name": "fish",
                    "amount": "1",
                    "evidence": "whole fish",
                    "source": "caption",
                }
            ],
        ) as collect_ing,
        patch(
            "recipe_kitchen.services.caption_pipeline.collect_steps",
            return_value=[
                {
                    "order": 1,
                    "instruction": "Fry the fish",
                    "evidence": "fry",
                    "source": "caption",
                }
            ],
        ) as collect_steps,
        patch("recipe_kitchen.services.caption_pipeline.is_burmese", return_value=False),
    ):
        extracted = extract_caption_channel("Fry a whole fish", source="caption")

    assert extracted.text_en == "Fry a whole fish"
    assert extracted.ingredients == [
        Ingredient(name="fish", amount="1", evidence="whole fish", source="caption")
    ]
    assert extracted.steps == [
        Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")
    ]
    collect_ing.assert_called_once_with("Fry a whole fish", source="caption")
    collect_steps.assert_called_once_with("Fry a whole fish", source="caption")


def test_extract_caption_channel_forwards_source() -> None:
    with (
        patch(
            "recipe_kitchen.services.caption_pipeline.collect_ingredients",
            return_value=[],
        ) as collect_ing,
        patch(
            "recipe_kitchen.services.caption_pipeline.collect_steps",
            return_value=[],
        ) as collect_steps,
        patch("recipe_kitchen.services.caption_pipeline.is_burmese", return_value=False),
    ):
        extract_caption_channel("Fry a whole fish", source="visual")

    collect_ing.assert_called_once_with("Fry a whole fish", source="visual")
    collect_steps.assert_called_once_with("Fry a whole fish", source="visual")

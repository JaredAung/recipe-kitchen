from unittest.mock import patch

from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.caption_pipeline import extract_caption_channel, looks_like_recipe

RECIPE_CAPTION = "Add 1 tsp salt and fry the fish in 2 tbsp oil."
BOURBON_CAPTION = (
    "Ep 13: Bourbon Chicken- 1 tsp Onion Powder - 1/3 cup soy sauce "
    "1. In a bowl, whisk together the soy sauce. 2. Season the chicken."
)
MARKETING_CAPTIONS = (
    "👉Spicy fried fish that will make even relatives forget👍😋",
    "👉 Delicious red pork cooked with sweet and fluffy 👍😋",
    (
        "I'm here to share with you a Chinese style Stir-Fried Minced Meat "
        "recipe that the whole house loves. 🥰"
    ),
    (
        "Crispy Potato Slices Quick process of making Potato Slices 😋 "
        "Simple visuals, satisfying result. Pure Kitchen ASMR, Original "
        "Cooking Visuals, Satisfying Food Journey, Relaxing Snack Prep, "
        "Global Recipe Discovery"
    ),
    "Maggi Omlette 🥪",
)


def test_looks_like_recipe_skips_marketing_captions() -> None:
    for caption in MARKETING_CAPTIONS:
        assert looks_like_recipe(caption) is False, caption
    assert looks_like_recipe("Fry a whole fish") is False
    assert looks_like_recipe("") is False


def test_looks_like_recipe_accepts_structured_captions() -> None:
    assert looks_like_recipe(BOURBON_CAPTION) is True
    assert looks_like_recipe(RECIPE_CAPTION) is True
    assert looks_like_recipe("- onion\n- garlic\n- salt") is True
    assert looks_like_recipe("Heat the oil. Add the pork. Simmer until tender.") is True


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


def test_extract_caption_channel_skips_marketing_without_gemini() -> None:
    caption = "Maggi Omlette 🥪"
    with (
        patch("recipe_kitchen.services.caption_pipeline.collect_ingredients") as collect_ing,
        patch("recipe_kitchen.services.caption_pipeline.collect_steps") as collect_steps,
        patch("recipe_kitchen.services.caption_pipeline.is_burmese", return_value=False),
    ):
        extracted = extract_caption_channel(caption, source="caption")

    assert extracted.ingredients == []
    assert extracted.steps == []
    assert extracted.source_text == caption
    assert extracted.text_en == caption
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
        extracted = extract_caption_channel(RECIPE_CAPTION, source="caption")

    assert extracted.text_en == RECIPE_CAPTION
    assert extracted.ingredients == [
        Ingredient(name="fish", amount="1", evidence="whole fish", source="caption")
    ]
    assert extracted.steps == [
        Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")
    ]
    collect_ing.assert_called_once_with(RECIPE_CAPTION, source="caption")
    collect_steps.assert_called_once_with(RECIPE_CAPTION, source="caption")


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
        extract_caption_channel(RECIPE_CAPTION, source="visual")

    collect_ing.assert_called_once_with(RECIPE_CAPTION, source="visual")
    collect_steps.assert_called_once_with(RECIPE_CAPTION, source="visual")

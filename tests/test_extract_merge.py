from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.extract_merge import merge_ingredients, merge_steps


def test_merge_ingredients_keeps_one_row_and_later_evidence() -> None:
    caption = Ingredient(name="Fish", amount="", evidence="spicy fried fish", source="caption")
    audio = Ingredient(name="fish", amount="1", evidence="washed fish", source="audio")

    merged = merge_ingredients([caption], [audio])

    assert merged == [
        Ingredient(name="fish", amount="1", evidence="washed fish", source="audio"),
    ]


def test_merge_ingredients_keeps_earlier_amount_when_later_is_empty() -> None:
    caption = Ingredient(name="onion", amount="two", evidence="two onions", source="caption")
    visual = Ingredient(name="Onion", amount="", evidence="sliced onion", source="visual")

    merged = merge_ingredients([caption], [visual])

    assert merged == [
        Ingredient(name="Onion", amount="two", evidence="sliced onion", source="visual"),
    ]


def test_merge_ingredients_collapses_duplicates_in_one_channel() -> None:
    first = Ingredient(name="salt", amount="", evidence="salt on onions", source="visual")
    second = Ingredient(name="salt", amount="", evidence="salt on the plate", source="visual")

    assert merge_ingredients([], [first, second]) == [second]


def test_merge_steps_drops_caption_title_and_renumbers() -> None:
    title = Step(order=1, instruction="Cook the red pork", evidence="red pork", source="caption")
    fry = Step(order=1, instruction="Fry the pork", evidence="fry", source="audio")
    simmer = Step(order=2, instruction="Simmer until tender", evidence="simmer", source="audio")

    merged = merge_steps([title], [fry, simmer])

    assert merged == [
        fry.model_copy(update={"order": 1}),
        simmer.model_copy(update={"order": 2}),
    ]


def test_merge_steps_keeps_real_caption_method() -> None:
    fry = Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")

    assert merge_steps([], [fry]) == [fry]


def test_merge_steps_collapses_duplicate_instructions() -> None:
    caption = Step(order=1, instruction="Heat the oil.", evidence="heat oil", source="caption")
    audio = Step(
        order=1,
        instruction="Heat the oil",
        evidence="when the oil is hot",
        source="audio",
    )

    assert merge_steps([caption], [audio]) == [audio]

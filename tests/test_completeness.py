from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.completeness import is_sufficient


def test_is_sufficient_false_without_ingredients_or_steps() -> None:
    ingredient = Ingredient(
        name="fish",
        amount="1",
        evidence="whole fish",
        source="caption",
    )
    step = Step(order=1, instruction="Fry the fish", evidence="fry", source="caption")

    empty = is_sufficient([], [])
    assert empty.sufficient is False
    assert empty.reason

    no_steps = is_sufficient([ingredient], [])
    assert no_steps.sufficient is False

    no_ingredients = is_sufficient([], [step])
    assert no_ingredients.sufficient is False

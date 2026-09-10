from unittest.mock import patch

from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.collect_bilingual import collect_bilingual


def test_collect_bilingual_reconciles_parallel_extracts() -> None:
    def collect_ing(text: str, source: str) -> list[dict[str, str]]:
        if text.startswith("ဆီ"):
            return [{"name": "ဆီ", "amount": "", "evidence": "ဆီထည့်", "source": source}]
        return [{"name": "oil", "amount": "1 tbsp", "evidence": "add oil", "source": source}]

    def collect_steps(text: str, source: str) -> list[dict[str, object]]:
        if text.startswith("ဆီ"):
            return [{"order": 1, "instruction": "ကြော်ပါ", "evidence": "ကြော်ပါ", "source": source}]
        return [{"order": 1, "instruction": "Fry", "evidence": "fry", "source": source}]

    with (
        patch(
            "recipe_kitchen.services.collect_bilingual.collect_ingredients",
            side_effect=collect_ing,
        ) as collect_ing_mock,
        patch(
            "recipe_kitchen.services.collect_bilingual.collect_steps",
            side_effect=collect_steps,
        ) as collect_steps_mock,
    ):
        ingredients, steps = collect_bilingual("ဆီထည့် ကြော်ပါ", "Add oil and fry", source="audio")

    assert collect_ing_mock.call_count == 2
    collect_ing_mock.assert_any_call("ဆီထည့် ကြော်ပါ", source="audio")
    collect_ing_mock.assert_any_call("Add oil and fry", source="audio")
    assert collect_steps_mock.call_count == 2
    assert ingredients == [Ingredient(name="oil", amount="1 tbsp", evidence="ဆီထည့်", source="audio")]
    assert steps == [Step(order=1, instruction="Fry", evidence="ကြော်ပါ", source="audio")]

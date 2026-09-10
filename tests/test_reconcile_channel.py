from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.reconcile_channel import reconcile_ingredients, reconcile_steps


def _ingredient(*, name: str, amount: str, evidence: str) -> Ingredient:
    return Ingredient(name=name, amount=amount, evidence=evidence, source="audio")


def _step(*, order: int, instruction: str, evidence: str) -> Step:
    return Step(order=order, instruction=instruction, evidence=evidence, source="caption")


def test_reconcile_ingredients_returns_english_when_burmese_is_empty() -> None:
    english = [_ingredient(name="oil", amount="1 tbsp", evidence="heat oil")]
    assert reconcile_ingredients([], english) == english


def test_reconcile_ingredients_returns_burmese_when_english_is_empty() -> None:
    burmese = [_ingredient(name="ဆီ", amount="", evidence="ဆီထည့်")]
    assert reconcile_ingredients(burmese, []) == burmese


def test_reconcile_ingredients_pairs_by_index_without_timestamps() -> None:
    from_my = [
        _ingredient(name="ဆီ", amount="၂ ဇွန်း", evidence="ဆီထည့်"),
        _ingredient(name="ဆား", amount="", evidence="ဆားထည့်"),
    ]
    from_en = [
        _ingredient(name="oil", amount="2 tbsp", evidence="add oil"),
        _ingredient(name="salt", amount="1 tsp", evidence="add salt"),
    ]

    merged = reconcile_ingredients(from_my, from_en)

    assert merged == [
        _ingredient(name="oil", amount="2 tbsp", evidence="ဆီထည့်"),
        _ingredient(name="salt", amount="1 tsp", evidence="ဆားထည့်"),
    ]


def test_reconcile_ingredients_keeps_burmese_amount_when_english_amount_is_blank() -> None:
    from_my = [_ingredient(name="ဆီ", amount="၂ ဇွန်း", evidence="ဆီထည့်")]
    from_en = [_ingredient(name="oil", amount="", evidence="add oil")]

    merged = reconcile_ingredients(from_my, from_en)

    assert merged == [_ingredient(name="oil", amount="၂ ဇွန်း", evidence="ဆီထည့်")]


def test_reconcile_ingredients_pairs_by_timestamp() -> None:
    from_my = [
        _ingredient(name="ဆား", amount="", evidence="[00:12] ဆားထည့်"),
        _ingredient(name="ဆီ", amount="", evidence="[00:03] ဆီထည့်"),
    ]
    from_en = [
        _ingredient(name="oil", amount="1 tbsp", evidence="[00:03] add oil"),
        _ingredient(name="salt", amount="1 tsp", evidence="[00:12] add salt"),
    ]

    merged = reconcile_ingredients(from_my, from_en)

    assert merged == [
        _ingredient(name="salt", amount="1 tsp", evidence="[00:12] ဆားထည့်"),
        _ingredient(name="oil", amount="1 tbsp", evidence="[00:03] ဆီထည့်"),
    ]


def test_reconcile_ingredients_keeps_unmatched_english_after_timestamp_merge() -> None:
    from_my = [_ingredient(name="ဆီ", amount="", evidence="[00:03] ဆီထည့်")]
    from_en = [
        _ingredient(name="oil", amount="1 tbsp", evidence="[00:03] add oil"),
        _ingredient(name="garlic", amount="2 cloves", evidence="[00:20] add garlic"),
    ]

    merged = reconcile_ingredients(from_my, from_en)

    assert merged == [
        _ingredient(name="oil", amount="1 tbsp", evidence="[00:03] ဆီထည့်"),
        _ingredient(name="garlic", amount="2 cloves", evidence="[00:20] add garlic"),
    ]


def test_reconcile_steps_pairs_by_order_and_renumbers() -> None:
    from_my = [
        _step(order=2, instruction="ကြော်ပါ", evidence="ကြော်ပါ"),
        _step(order=1, instruction="ဆီထည့်", evidence="ဆီထည့်"),
    ]
    from_en = [
        _step(order=1, instruction="Add oil", evidence="add oil"),
        _step(order=2, instruction="Fry", evidence="fry"),
    ]

    merged = reconcile_steps(from_my, from_en)

    assert merged == [
        _step(order=1, instruction="Add oil", evidence="ဆီထည့်"),
        _step(order=2, instruction="Fry", evidence="ကြော်ပါ"),
    ]


def test_reconcile_steps_appends_english_only_orders() -> None:
    from_my = [_step(order=1, instruction="ဆီထည့်", evidence="ဆီထည့်")]
    from_en = [
        _step(order=1, instruction="Add oil", evidence="add oil"),
        _step(order=2, instruction="Fry", evidence="fry"),
    ]

    merged = reconcile_steps(from_my, from_en)

    assert merged == [
        _step(order=1, instruction="Add oil", evidence="ဆီထည့်"),
        _step(order=2, instruction="Fry", evidence="fry"),
    ]

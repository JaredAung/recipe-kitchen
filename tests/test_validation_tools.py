from recipe_kitchen.schemas.recipe import Ingredient, Step
from recipe_kitchen.services.validation_tools import (
    audit_extract,
    generic_ingredient_names,
    source_corpus,
    ungrounded_evidence,
    validation_confidence,
)

FISH = Ingredient(name="fish", amount="1", evidence="whole fish", source="caption")
FRY = Step(order=1, instruction="Fry the fish", evidence="fry the fish", source="caption")


def test_ungrounded_evidence_flags_quotes_not_in_source() -> None:
    invented = Ingredient(name="msg", amount="", evidence="add msg now", source="caption")
    corpus = source_corpus(caption="Fry a whole fish in oil")
    issues = ungrounded_evidence([invented], [], corpus=corpus)
    assert [issue.code for issue in issues] == ["ungrounded_evidence"]
    assert issues[0].name == "msg"


def test_ungrounded_evidence_accepts_caption_quotes() -> None:
    corpus = source_corpus(caption="Fry the fish with a whole fish")
    assert ungrounded_evidence([FISH], [FRY], corpus=corpus) == []


def test_ungrounded_evidence_skips_visual_descriptions() -> None:
    pepper = Ingredient(
        name="capsicum",
        amount="",
        evidence="red dice from a labeled packet",
        source="visual",
    )
    issues = ungrounded_evidence([pepper], [], corpus="spoken transcript only")
    assert issues == []


def test_ungrounded_evidence_flags_generic_visual_quotes() -> None:
    pepper = Ingredient(name="capsicum", amount="", evidence="from the video", source="visual")
    issues = ungrounded_evidence([pepper], [], corpus="")
    assert issues[0].code == "ungrounded_evidence"
    assert issues[0].name == "capsicum"


def test_generic_ingredient_names_flags_vague_labels() -> None:
    spices = Ingredient(name="spices", amount="", evidence="add spices", source="visual")
    chili = Ingredient(name="chili powder", amount="", evidence="chili", source="visual")
    issues = generic_ingredient_names([spices, chili])
    assert [issue.name for issue in issues] == ["spices"]
    assert issues[0].code == "generic_name"


def test_audit_extract_scores_issues() -> None:
    spices = Ingredient(name="spices", amount="", evidence="from the video", source="visual")
    issues, confidence = audit_extract([spices], [], corpus="")
    assert {issue.code for issue in issues} == {"ungrounded_evidence", "generic_name"}
    assert confidence == validation_confidence(issues)
    assert confidence < 1.0
    assert audit_extract([FISH], [FRY], corpus="Fry the fish with a whole fish")[1] == 1.0

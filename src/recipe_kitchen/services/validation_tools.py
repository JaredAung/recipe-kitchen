"""Deterministic extract audits: ungrounded evidence and generic ingredient names."""

from __future__ import annotations

import re

from recipe_kitchen.schemas.extract import ValidationIssue
from recipe_kitchen.schemas.recipe import Ingredient, Step

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_GENERIC_NAMES = frozenset(
    {
        "ingredient",
        "ingredients",
        "spice",
        "spices",
        "seasoning",
        "seasonings",
        "garnish",
        "mix",
        "mixture",
        "powder",
        "sauce",
        "starch",
        "condiment",
        "flavoring",
    }
)
_GENERIC_EVIDENCE = frozenset(
    {
        "from the video",
        "from video",
        "from the caption",
        "from caption",
        "from audio",
        "shown on screen",
        "seen on screen",
        "visual",
        "overlay",
        "the recipe",
    }
)
_UNGROUNDED_PENALTY = 0.2
_GENERIC_PENALTY = 0.15


def _fold(text: str) -> str:
    return " ".join(_PUNCT.sub(" ", text.casefold()).split())


def source_corpus(
    *,
    caption: str = "",
    subtitle_text: str = "",
    transcript_en: str = "",
    transcript_my: str | None = None,
    text_en: str = "",
    text_my: str | None = None,
) -> str:
    """Join channel text that caption/audio evidence should quote."""
    parts = [
        caption,
        subtitle_text,
        transcript_en,
        transcript_my or "",
        text_en,
        text_my or "",
    ]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _evidence_in_corpus(evidence: str, corpus: str) -> bool:
    folded_evidence = _fold(evidence)
    folded_corpus = _fold(corpus)
    if not folded_evidence or not folded_corpus:
        return False
    if folded_evidence in folded_corpus:
        return True
    tokens = [token for token in folded_evidence.split() if len(token) > 1]
    if len(tokens) >= 3:
        return sum(token in folded_corpus for token in tokens) / len(tokens) >= 0.7
    return False


def ungrounded_evidence(
    ingredients: list[Ingredient],
    steps: list[Step],
    *,
    corpus: str,
) -> list[ValidationIssue]:
    """Flag quotes missing from source text, or generic visual evidence.

    Visual evidence is a description, not a transcript quote.
    """
    folded_generic = {_fold(phrase) for phrase in _GENERIC_EVIDENCE}
    issues: list[ValidationIssue] = []

    def check(*, kind: str, evidence: str, source: str, name: str) -> None:
        quote = evidence.strip()
        if not quote:
            issues.append(
                ValidationIssue(
                    code="ungrounded_evidence",
                    detail=f"{kind} has no evidence",
                    name=name,
                    source=source,
                )
            )
            return
        if _fold(quote) in folded_generic or len(_fold(quote)) < 3:
            issues.append(
                ValidationIssue(
                    code="ungrounded_evidence",
                    detail=f"{kind} evidence is generic",
                    name=name,
                    source=source,
                    evidence=quote,
                )
            )
            return
        if source == "visual":
            return
        if not _evidence_in_corpus(quote, corpus):
            issues.append(
                ValidationIssue(
                    code="ungrounded_evidence",
                    detail=f"{kind} evidence is not in the source text",
                    name=name,
                    source=source,
                    evidence=quote,
                )
            )

    for item in ingredients:
        check(kind="ingredient", evidence=item.evidence, source=item.source, name=item.name)
    for step in steps:
        check(
            kind="step",
            evidence=step.evidence,
            source=step.source,
            name=step.instruction,
        )
    return issues


def generic_ingredient_names(ingredients: list[Ingredient]) -> list[ValidationIssue]:
    """Flag ingredient names that are too vague to cook from."""
    issues: list[ValidationIssue] = []
    for item in ingredients:
        if _fold(item.name) in _GENERIC_NAMES:
            issues.append(
                ValidationIssue(
                    code="generic_name",
                    detail="ingredient name is too vague",
                    name=item.name,
                    source=item.source,
                    evidence=item.evidence,
                )
            )
    return issues


def validation_confidence(issues: list[ValidationIssue]) -> float:
    """Return 0-1 from issue counts. Does not re-judge cookability."""
    score = 1.0
    for issue in issues:
        if issue.code == "ungrounded_evidence":
            score -= _UNGROUNDED_PENALTY
        elif issue.code == "generic_name":
            score -= _GENERIC_PENALTY
    return round(max(0.0, min(1.0, score)), 3)


def audit_extract(
    ingredients: list[Ingredient],
    steps: list[Step],
    *,
    corpus: str,
) -> tuple[list[ValidationIssue], float]:
    """Run grounding and generic-name checks and score the extract."""
    issues = [
        *ungrounded_evidence(ingredients, steps, corpus=corpus),
        *generic_ingredient_names(ingredients),
    ]
    return issues, validation_confidence(issues)

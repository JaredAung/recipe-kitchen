"""Merge ingredients and steps when a later extract channel runs."""

from __future__ import annotations

import re

from recipe_kitchen.schemas.recipe import Ingredient, Step

_TITLE_VERBS = frozenset({"cook", "make", "prepare", "enjoy", "try"})
_TITLE_DETAIL = re.compile(
    r"\b(until|with|in|into|for|over|then|and|add|mix|heat|fry|slice|season)\b"
)


def _norm_name(name: str) -> str:
    return " ".join(name.casefold().split())


def _norm_instruction(instruction: str) -> str:
    return " ".join(instruction.casefold().rstrip(".!").split())


def _is_title_step(step: Step) -> bool:
    """True for a caption line that restates the dish instead of a method."""
    if step.source != "caption":
        return False
    text = step.instruction.casefold().rstrip(".!")
    words = text.split()
    if not words or len(words) > 6:
        return False
    if words[0] not in _TITLE_VERBS:
        return False
    return _TITLE_DETAIL.search(text) is None


def merge_ingredients(
    existing: list[Ingredient],
    incoming: list[Ingredient],
) -> list[Ingredient]:
    """Keep one row per ingredient name. Later channel wins; keep a non-empty amount."""
    index_by_name: dict[str, int] = {}
    merged: list[Ingredient] = []
    for item in (*existing, *incoming):
        key = _norm_name(item.name)
        if key not in index_by_name:
            index_by_name[key] = len(merged)
            merged.append(item)
            continue
        prev = merged[index_by_name[key]]
        amount = item.amount.strip() or prev.amount
        merged[index_by_name[key]] = item.model_copy(update={"amount": amount})
    return merged


def merge_steps(existing: list[Step], incoming: list[Step]) -> list[Step]:
    """Drop caption title steps, collapse duplicate instructions, and renumber."""
    index_by_instruction: dict[str, int] = {}
    merged: list[Step] = []
    for item in (*existing, *incoming):
        if _is_title_step(item):
            continue
        key = _norm_instruction(item.instruction)
        if key not in index_by_instruction:
            index_by_instruction[key] = len(merged)
            merged.append(item)
            continue
        merged[index_by_instruction[key]] = item
    return [step.model_copy(update={"order": order}) for order, step in enumerate(merged, start=1)]

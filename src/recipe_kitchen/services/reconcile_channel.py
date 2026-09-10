"""Pair Burmese and English extracts of the same channel mention."""

from __future__ import annotations

import re

from recipe_kitchen.schemas.recipe import Ingredient, Step

_TIMESTAMP = re.compile(r"\[(\d{1,2}):(\d{2})\]")


def _timestamp_seconds(text: str) -> int | None:
    match = _TIMESTAMP.search(text)
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def _blend_ingredient(from_my: Ingredient | None, from_en: Ingredient | None) -> Ingredient:
    """English kitchen name and amount; Burmese evidence when both exist."""
    if from_my is None:
        if from_en is None:
            raise ValueError("Need a Burmese or English ingredient to blend.")
        return from_en
    if from_en is None:
        return from_my
    return from_my.model_copy(
        update={
            "name": from_en.name.strip() or from_my.name,
            "amount": from_en.amount.strip() or from_my.amount,
            "evidence": from_my.evidence.strip() or from_en.evidence,
        }
    )


def _blend_step(from_my: Step | None, from_en: Step | None) -> Step:
    """English instruction; Burmese evidence when both exist."""
    if from_my is None:
        if from_en is None:
            raise ValueError("Need a Burmese or English step to blend.")
        return from_en
    if from_en is None:
        return from_my
    return from_my.model_copy(
        update={
            "instruction": from_en.instruction.strip() or from_my.instruction,
            "evidence": from_my.evidence.strip() or from_en.evidence,
        }
    )


def reconcile_ingredients(
    from_my: list[Ingredient],
    from_en: list[Ingredient],
) -> list[Ingredient]:
    """One row per mention. Pair by timestamp, else by list order."""
    if not from_my:
        return list(from_en)
    if not from_en:
        return list(from_my)

    my_has_ts = any(_timestamp_seconds(item.evidence) is not None for item in from_my)
    en_has_ts = any(_timestamp_seconds(item.evidence) is not None for item in from_en)
    if my_has_ts and en_has_ts:
        return _pair_ingredients_by_timestamp(from_my, from_en)

    count = max(len(from_my), len(from_en))
    return [
        _blend_ingredient(
            from_my[index] if index < len(from_my) else None,
            from_en[index] if index < len(from_en) else None,
        )
        for index in range(count)
    ]


def _pair_ingredients_by_timestamp(
    from_my: list[Ingredient],
    from_en: list[Ingredient],
) -> list[Ingredient]:
    """Match mentions that share a [MM:SS] stamp; keep leftover English rows."""
    en_by_ts: dict[int, Ingredient] = {}
    extras: list[Ingredient] = []
    for item in from_en:
        stamp = _timestamp_seconds(item.evidence)
        if stamp is None or stamp in en_by_ts:
            extras.append(item)
        else:
            en_by_ts[stamp] = item

    merged: list[Ingredient] = []
    used: set[int] = set()
    for item in from_my:
        stamp = _timestamp_seconds(item.evidence)
        english = en_by_ts.get(stamp) if stamp is not None else None
        if stamp is not None and english is not None:
            used.add(stamp)
        merged.append(_blend_ingredient(item, english))
    for stamp, item in en_by_ts.items():
        if stamp not in used:
            merged.append(item)
    merged.extend(extras)
    return merged


def reconcile_steps(from_my: list[Step], from_en: list[Step]) -> list[Step]:
    """One row per step order. English instruction, Burmese evidence."""
    if not from_my:
        return _renumber(from_en)
    if not from_en:
        return _renumber(from_my)

    my_by_order, my_extras = _index_steps(from_my)
    en_by_order, extras = _index_steps(from_en)
    merged: list[Step] = []
    used: set[int] = set()
    for order in sorted(my_by_order):
        english = en_by_order.get(order)
        if english is not None:
            used.add(order)
        merged.append(_blend_step(my_by_order[order], english))
    for order, item in sorted(en_by_order.items()):
        if order not in used:
            merged.append(item)
    merged.extend(my_extras)
    merged.extend(extras)
    return _renumber(merged)


def _index_steps(steps: list[Step]) -> tuple[dict[int, Step], list[Step]]:
    by_order: dict[int, Step] = {}
    extras: list[Step] = []
    for item in steps:
        if item.order in by_order:
            extras.append(item)
        else:
            by_order[item.order] = item
    return by_order, extras


def _renumber(steps: list[Step]) -> list[Step]:
    return [step.model_copy(update={"order": order}) for order, step in enumerate(steps, start=1)]

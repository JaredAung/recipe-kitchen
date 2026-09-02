from __future__ import annotations

from pydantic import BaseModel

from recipe_kitchen.schemas.recipe import Ingredient, Step


class Sufficiency(BaseModel):
    sufficient: bool
    reason: str = ""


class CaptionExtract(BaseModel):
    ingredients: list[Ingredient]
    steps: list[Step]
    source_text: str = ""
    text_my: str | None = None
    text_en: str = ""


class AudioExtract(BaseModel):
    transcript_my: str | None = None
    transcript_en: str
    ingredients: list[Ingredient]
    steps: list[Step]

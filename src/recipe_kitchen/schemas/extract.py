from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from recipe_kitchen.schemas.recipe import Ingredient, Step

StoppedAfter = Literal["caption", "subtitle", "audio", "visual"]


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


class RecipeGraphState(BaseModel):
    caption: str = ""
    subtitle_text: str = ""
    video_path: str | None = None
    video_storage_path: str | None = None
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    transcript_my: str | None = None
    transcript_en: str = ""
    sufficient: bool = False
    reason: str = ""
    phase: StoppedAfter | None = None
    text_my: str | None = None
    text_en: str = ""
    visual_text: str = ""


class RecipePipelineResult(BaseModel):
    id: str = ""
    stopped_after: StoppedAfter
    sufficient: bool
    reason: str = ""
    transcript_my: str | None = None
    transcript_en: str
    ingredients: list[Ingredient]
    steps: list[Step]
    caption_text: str = ""

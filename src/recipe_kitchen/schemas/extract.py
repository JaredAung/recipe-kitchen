from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from recipe_kitchen.schemas.recipe import Ingredient, Step

StoppedAfter = Literal["caption", "subtitle", "audio", "visual"]
ValidationCode = Literal["ungrounded_evidence", "generic_name"]


class Sufficiency(BaseModel):
    sufficient: bool
    reason: str = ""


class ValidationIssue(BaseModel):
    code: ValidationCode
    severity: Literal["warning"] = "warning"
    detail: str
    name: str = ""
    source: str = ""
    evidence: str = ""


class RecipeMetadata(BaseModel):
    title: str
    cuisine: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    total_time_minutes: int | None = Field(default=None, ge=0)


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
    title: str = ""
    cuisine: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    total_time_minutes: int | None = None
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    validation_confidence: float | None = None
    phase: StoppedAfter | None = None
    text_my: str | None = None
    text_en: str = ""
    visual_text: str = ""
    audio_has_speech: bool = True
    save: bool = False
    original_filename: str | None = None
    source_url: str | None = None
    thumbnail_path: str | None = None
    recipe_id: str = ""


class RecipePipelineResult(BaseModel):
    id: str = ""
    stopped_after: StoppedAfter
    sufficient: bool
    reason: str = ""
    title: str = ""
    cuisine: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    total_time_minutes: int | None = None
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    validation_confidence: float | None = None
    transcript_my: str | None = None
    transcript_en: str
    ingredients: list[Ingredient]
    steps: list[Step]
    caption_text: str = ""

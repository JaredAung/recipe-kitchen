from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)

CollectorSource = Literal["audio", "caption", "visual"]
Difficulty = Literal["easy", "medium", "hard"]
Visibility = Literal["private", "unlisted", "public"]
RecipeStatus = Literal["processing", "ready", "failed"]


class Ingredient(BaseModel):
    name: str = Field(min_length=1)
    amount: str = ""
    evidence: str = Field(min_length=1)
    source: CollectorSource

    @field_validator("name", "amount", "evidence", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim leading and trailing whitespace from string fields."""
        return value.strip() if isinstance(value, str) else value


class Step(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order: int = Field(ge=1, validation_alias=AliasChoices("order", "step_order"))
    instruction: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    source: CollectorSource

    @field_validator("instruction", "evidence", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim leading and trailing whitespace from string fields."""
        return value.strip() if isinstance(value, str) else value


class RecipeCreate(BaseModel):
    transcript_my: str | None = Field(default=None, min_length=1)
    transcript_en: str = Field(min_length=1)
    ingredients: list[Ingredient] = Field(min_length=1)
    steps: list[Step] = Field(min_length=1)
    user_id: UUID | None = None
    title: str | None = None
    description: str | None = None
    cuisine: str = "burmese"
    tags: list[str] = Field(default_factory=list)
    prep_time_minutes: int | None = Field(default=None, ge=0)
    cook_time_minutes: int | None = Field(default=None, ge=0)
    total_time_minutes: int | None = Field(default=None, ge=0)
    difficulty: Difficulty = "medium"
    source_url: str | None = None
    original_filename: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    video_path: str | None = None
    thumbnail_path: str | None = None
    caption_text: str = ""
    extraction_meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("transcript_my", "transcript_en", "caption_text", mode="before")
    @classmethod
    def strip_text(cls, value: object, info: ValidationInfo) -> object:
        """Trim string fields. Blank `transcript_my` becomes None."""
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if info.field_name == "transcript_my" and not stripped:
            return None
        return stripped


class VisualExtract(BaseModel):
    ingredients: list[Ingredient]
    steps: list[Step]
    transcript_en: str
    usage: dict[str, Any] = Field(default_factory=dict)

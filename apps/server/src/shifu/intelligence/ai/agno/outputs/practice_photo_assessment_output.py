from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class PracticeCriterionOutput(BaseModel):
    """One criterion: an allowed level with its predefined comment key, or inconclusive."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    key: str = Field(min_length=1, max_length=128)
    level: Literal[0, 25, 50, 75, 100] | None
    comment_key: str | None = Field(max_length=128)


class PracticeRecordOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    record_key: str = Field(min_length=1, max_length=128)
    sufficient: bool


class PracticePhotoAssessmentOutput(BaseModel):
    """Closed output: only observations, never a grade, text or recommendation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    criteria: list[PracticeCriterionOutput] = Field(max_length=40)
    records: list[PracticeRecordOutput] = Field(max_length=5)

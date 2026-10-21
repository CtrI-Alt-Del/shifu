from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class MentorReviewCriterionOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    choice: Literal['approved', 'rejected', 'inconclusive']
    feedback: str = Field(max_length=400)

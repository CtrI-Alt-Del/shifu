from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

MAX_QUESTIONS = 4
MIN_OPTIONS = 2
MAX_OPTIONS = 6


class PlanningQuestionOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    text: str
    kind: Literal['single', 'multiple']
    options: list[str]
    allow_unknown: bool

    @model_validator(mode='after')
    def _bounded(self) -> Self:
        if not self.text.strip():
            raise ValueError('A question needs a text')
        if not MIN_OPTIONS <= len(self.options) <= MAX_OPTIONS or any(
            not option.strip() for option in self.options
        ):
            raise ValueError('A question needs between two and six options')
        return self


class PlanningInterviewOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    needs_clarification: bool
    questions: list[PlanningQuestionOutput]

    @model_validator(mode='after')
    def _consistent(self) -> Self:
        if self.needs_clarification and not 1 <= len(self.questions) <= MAX_QUESTIONS:
            raise ValueError('A clarification needs between one and four questions')
        return self

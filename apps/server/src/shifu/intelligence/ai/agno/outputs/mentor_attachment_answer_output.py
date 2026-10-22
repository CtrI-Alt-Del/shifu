from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shifu.intelligence.ai.agno.outputs.mentor_attachment_source_output import (
    MentorAttachmentSourceOutput,
)


class MentorAttachmentAnswerOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    answer: str = Field(min_length=1, max_length=4000)
    sources: list[MentorAttachmentSourceOutput] = Field(max_length=12)

    @field_validator('answer')
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('The answer must contain text')
        return value

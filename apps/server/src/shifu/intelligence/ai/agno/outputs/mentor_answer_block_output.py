from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent


class MentorAnswerBlockOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    block_key: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    intent: MentorIntent | None = None
    content: str = Field(min_length=1)

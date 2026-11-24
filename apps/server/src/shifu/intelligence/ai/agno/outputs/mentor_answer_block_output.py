from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shifu.intelligence.ai.agno.outputs.mentor_attachment_source_output import (
    MentorAttachmentSourceOutput,
)
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent


class MentorAnswerBlockOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    block_key: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    intent: MentorIntent | None = None
    content: str = Field(min_length=1)
    sources: list[MentorAttachmentSourceOutput] = Field(
        default_factory=list[MentorAttachmentSourceOutput]
    )

    @field_validator('intent')
    @classmethod
    def drop_action_intent(cls, intent: MentorIntent | None) -> MentorIntent | None:
        # Only the Core's local route builds an action; a generated block never
        # does. The model may still label its text as one, so the label is dropped
        # rather than failing the whole answer.
        if intent in {MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL}:
            return None
        return intent

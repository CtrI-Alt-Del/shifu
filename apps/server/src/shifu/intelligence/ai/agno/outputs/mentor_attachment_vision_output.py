from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MentorAttachmentVisionOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    legible: bool
    description: str = Field(max_length=6000)

    @model_validator(mode='after')
    def _consistent_legibility(self) -> 'MentorAttachmentVisionOutput':
        if self.legible == (not self.description.strip()):
            raise ValueError('Legibility and description are inconsistent')
        return self

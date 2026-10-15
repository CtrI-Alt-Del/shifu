from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class MentorAttachmentSourceOutput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', strict=True)
    attachment_id: str = Field(min_length=26, max_length=26)
    chunk_id: str = Field(min_length=26, max_length=26)
    page_number: int | None = Field(default=None, ge=1)
    locator: str = Field(min_length=1, max_length=256)

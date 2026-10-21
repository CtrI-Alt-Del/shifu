from datetime import datetime

from pydantic import UUID4, BaseModel, ConfigDict, Field

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus


class CreateBatchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_id: str | None = None


class UploadAttachmentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    upload_key: UUID4


class Attachment(BaseModel):
    attachment_id: str
    filename: str
    media_type: str
    size_bytes: int
    status: MentorAttachmentStatus
    failure_code: str | None
    analyzed_pages: list[int]
    illegible_pages: list[int]
    uninterpreted_pages: list[int]


class Batch(BaseModel):
    batch_id: str
    expires_at: datetime
    attachments: list[Attachment] = Field(default_factory=list)


class BatchCreated(BaseModel):
    batch_id: str
    expires_at: datetime

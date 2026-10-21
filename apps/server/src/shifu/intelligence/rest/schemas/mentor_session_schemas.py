from datetime import datetime

from pydantic import BaseModel, Field

from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    LearnerMemoryChangeKind,
    MentorAttachmentStatus,
)
from shifu.intelligence.core.domain.structures import MentorResponseSnapshot


class MentorSessionSchemas:
    class Session(BaseModel):
        id: str
        title: str
        created_at: datetime
        updated_at: datetime
        last_activity_at: datetime

    class Message(BaseModel):
        id: str
        session_id: str
        role: str
        content: str
        created_at: datetime
        in_reply_to_message_id: str | None
        attachments: list['MentorSessionSchemas.Attachment'] = []

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

    class MessagesPage(BaseModel):
        items: list['MentorSessionSchemas.Message']
        next_cursor: str | None

    class SessionsPage(BaseModel):
        items: list['MentorSessionSchemas.Session']
        next_cursor: str | None

    class SummaryMarker(BaseModel):
        version: int
        boundary_message_id: str
        covered_message_count: int
        completed_at: datetime
        after_message_id: str | None = None

    class SummaryState(BaseModel):
        current: 'MentorSessionSchemas.SummaryMarker | None' = None
        failure_after_message_id: str | None = None

    class MemoryItem(BaseModel):
        id: str = Field(validation_alias='change_id')
        source_message_id: str
        kind: LearnerMemoryChangeKind
        category: LearnerMemoryCategory
        memory_id: str | None
        content: str | None
        previous_content: str | None
        created_at: datetime

    class Detail(BaseModel):
        session: 'MentorSessionSchemas.Session'
        messages: 'MentorSessionSchemas.MessagesPage'
        pending_learner_message_id: str | None
        response: MentorResponseSnapshot | None = None
        summary: 'MentorSessionSchemas.SummaryState'
        memory_items: list['MentorSessionSchemas.MemoryItem'] = []

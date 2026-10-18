from datetime import datetime

from shifu.intelligence.core.domain.structures.mentor_attachment_view import (
    MentorAttachmentView,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentBatchView:
    batch_id: str
    expires_at: datetime
    attachments: tuple[MentorAttachmentView, ...]

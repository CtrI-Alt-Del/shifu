from __future__ import annotations

from typing import TYPE_CHECKING

from shifu.shared.core.domain.entities import frozen_entity

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.enums import MentorMessageRole
    from shifu.intelligence.core.domain.structures.mentor_attachment_view import (
        MentorAttachmentView,
    )


@frozen_entity
class MentorMessage:
    id: str
    session_id: str
    role: MentorMessageRole
    content: str
    created_at: datetime
    in_reply_to_message_id: str | None
    attachments: tuple[MentorAttachmentView, ...] = ()

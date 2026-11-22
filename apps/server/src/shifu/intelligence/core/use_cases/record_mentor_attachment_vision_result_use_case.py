from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.structures import (
        MentorAttachmentVisionResult,
    )
    from shifu.intelligence.core.interfaces import IntelligenceDatabase
    from shifu.shared.core.interfaces import ClockProvider

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentNotFoundError,
)


class RecordMentorAttachmentVisionResultUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider

    def execute(
        self,
        attachment_id: str,
        generation: int,
        execution_owner: str,
        result: MentorAttachmentVisionResult,
    ) -> None:
        if generation < 1 or not execution_owner.strip():
            raise MentorAttachmentConflictError
        now: datetime = self._clock_provider.now()
        with self._database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if attachment is None:
                raise MentorAttachmentNotFoundError
            if (
                attachment.status is not MentorAttachmentStatus.PROCESSING
                or attachment.generation != generation
                or attachment.execution_owner != execution_owner
                or attachment.claim_expires_at is None
                or attachment.claim_expires_at <= now
            ):
                raise MentorAttachmentConflictError
            attachment.record_vision_result(generation, execution_owner, result)
            repositories.mentor_attachments.update(attachment)

from datetime import datetime

from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentInvalidError,
)
from shifu.shared.core.domain.entities import entity


@entity
class MentorAttachmentBatch:
    id: str
    account_id: str
    session_id: str | None
    generation: int
    expires_at: datetime
    consumed_by_message_id: str | None
    revoked_at: datetime | None

    @classmethod
    def create(
        cls,
        batch_id: str,
        account_id: str,
        session_id: str | None,
        now: datetime,
        expires_at: datetime,
    ) -> 'MentorAttachmentBatch':
        if not batch_id.strip() or not account_id.strip() or expires_at <= now:
            raise MentorAttachmentInvalidError
        if session_id is not None and not session_id.strip():
            raise MentorAttachmentInvalidError
        return cls(
            id=batch_id,
            account_id=account_id,
            session_id=session_id,
            generation=1,
            expires_at=expires_at,
            consumed_by_message_id=None,
            revoked_at=None,
        )

    def consume(self, message_id: str) -> None:
        if not message_id.strip():
            raise MentorAttachmentInvalidError
        if self.revoked_at is not None or self.consumed_by_message_id is not None:
            if self.consumed_by_message_id == message_id:
                return
            raise MentorAttachmentConflictError
        self.consumed_by_message_id = message_id

    def renew(self, expires_at: datetime) -> None:
        if self.revoked_at is not None or self.consumed_by_message_id is not None:
            raise MentorAttachmentConflictError
        if expires_at <= self.expires_at:
            raise MentorAttachmentConflictError
        self.expires_at = expires_at
        self.generation += 1

    def revoke(self, now: datetime) -> None:
        if self.revoked_at is None:
            self.revoked_at = now
            self.generation += 1

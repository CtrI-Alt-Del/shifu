from datetime import datetime
from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorAttachment


class MentorAttachmentsRepository(Protocol):
    def find_by_id(
        self, attachment_id: str, *, for_update: bool = False
    ) -> MentorAttachment | None: ...

    def find_by_upload_key(
        self, batch_id: str, upload_key: str
    ) -> MentorAttachment | None: ...

    def find_by_batch_id(self, batch_id: str) -> tuple[MentorAttachment, ...]: ...

    def find_by_message_id(self, message_id: str) -> tuple[MentorAttachment, ...]: ...

    def find_by_session_id(
        self, account_id: str, session_id: str
    ) -> tuple[MentorAttachment, ...]: ...

    def find_for_cleanup(
        self,
        account_id: str,
        session_id: str | None,
        batch_id: str | None,
        *,
        removed_only: bool = True,
    ) -> tuple[MentorAttachment, ...]: ...

    def count_active_in_batch(self, batch_id: str) -> int: ...

    def add(self, attachment: MentorAttachment) -> None: ...

    def update(self, attachment: MentorAttachment) -> None: ...

    def remove(self, attachment_id: str) -> None: ...

    def find_expired_reservations(
        self, now: datetime, limit: int
    ) -> tuple[MentorAttachment, ...]: ...

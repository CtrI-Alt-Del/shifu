from datetime import datetime
from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorAttachmentBatch


class MentorAttachmentBatchesRepository(Protocol):
    def find_by_id(
        self, batch_id: str, *, for_update: bool = False
    ) -> MentorAttachmentBatch | None: ...

    def add(self, batch: MentorAttachmentBatch) -> None: ...

    def update(self, batch: MentorAttachmentBatch) -> None: ...

    def find_by_account_id(
        self, account_id: str
    ) -> tuple[MentorAttachmentBatch, ...]: ...

    def find_by_session_id(
        self, account_id: str, session_id: str
    ) -> tuple[MentorAttachmentBatch, ...]: ...

    def find_expired(
        self, now: datetime, limit: int
    ) -> tuple[MentorAttachmentBatch, ...]: ...

    def remove(self, batch_id: str) -> None: ...

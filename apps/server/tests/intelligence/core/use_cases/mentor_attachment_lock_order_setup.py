from collections.abc import Iterator
from typing import Any, cast

from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)


class LockRecorder:
    """Records row-lock acquisition across mocked mentor attachment repositories.

    Batch reads are scripted call by call (unlocked peeks and locked reads share
    the sequence) so tests can simulate a batch whose session binding changes
    between the peek and the lock.
    """

    def __init__(
        self,
        repositories: Any,
        batches: Iterator[MentorAttachmentBatch | None],
        *,
        session_available: bool = True,
    ) -> None:
        self.order: list[str] = []
        self._batches = batches
        self._session_available = session_available
        attachments = repositories.mentor_attachments.find_by_id
        self._attachment_side_effect: Any = attachments.side_effect
        self._attachment_value: MentorAttachment | None = attachments.return_value
        repositories.mentor_attachment_batches.find_by_id.side_effect = self._find_batch
        attachments.side_effect = self._find_attachment
        repositories.mentor_sessions.find_by_id_for_update.side_effect = (
            self._lock_session
        )

    def _find_batch(
        self, batch_id: str, *, for_update: bool = False
    ) -> MentorAttachmentBatch | None:
        del batch_id
        if for_update:
            self.order.append('batch')
        return next(self._batches)

    def _find_attachment(
        self, attachment_id: str, *, for_update: bool = False
    ) -> MentorAttachment | None:
        if for_update:
            self.order.append('attachment')
        side_effect = self._attachment_side_effect
        if side_effect is not None:
            return cast(
                'MentorAttachment | None',
                side_effect(attachment_id, for_update=for_update),
            )
        return self._attachment_value

    def _lock_session(self, account_id: str, session_id: str) -> object | None:
        del account_id, session_id
        self.order.append('session')
        return object() if self._session_available else None

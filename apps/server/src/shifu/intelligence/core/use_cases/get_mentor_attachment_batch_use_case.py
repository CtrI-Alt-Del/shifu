from datetime import timedelta

from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentNotFoundError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    MentorAttachmentCleanupRequestedEvent,
    MentorAttachmentCleanupRequestedPayload,
)
from shifu.intelligence.core.domain.structures import MentorAttachmentBatchView
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_attachment_helpers import (
    attachment_batch_view,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    MentorAccessProvider,
)


class GetMentorAttachmentBatchUseCase:
    _INACTIVITY = timedelta(hours=1)

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(self, account_id: str, batch_id: str) -> MentorAttachmentBatchView:
        grant = self._access_provider.authorize(account_id, batch_id)
        self._access_provider.assert_current(grant)
        now = self._clock_provider.now()
        with self._database.transaction() as repositories:
            batch = repositories.mentor_attachment_batches.find_by_id(
                batch_id, for_update=True
            )
            if (
                batch is None
                or batch.account_id != account_id
                or batch.revoked_at is not None
            ):
                raise MentorAttachmentNotFoundError
            if batch.expires_at <= now and batch.consumed_by_message_id is None:
                raise MentorAttachmentConflictError
            if batch.session_id is not None:
                session = repositories.mentor_sessions.find_by_id_for_update(
                    account_id, batch.session_id
                )
                if session is None:
                    raise MentorSessionNotFoundError
            if batch.consumed_by_message_id is None:
                new_expiry = now + self._INACTIVITY
                if new_expiry > batch.expires_at:
                    batch.renew(new_expiry)
                    repositories.mentor_attachment_batches.update(batch)
                    repositories.events.add(
                        MentorAttachmentCleanupRequestedEvent(
                            payload=MentorAttachmentCleanupRequestedPayload(
                                account_id=account_id,
                                session_id=None,
                                batch_id=batch.id,
                                deletion_generation=batch.generation,
                            )
                        ),
                        available_at=batch.expires_at,
                    )
            self._access_provider.assert_current(grant)
            return attachment_batch_view(repositories, batch.id, batch.expires_at)

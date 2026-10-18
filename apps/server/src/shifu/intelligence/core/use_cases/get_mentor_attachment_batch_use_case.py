from datetime import datetime, timedelta

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
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases.mentor_attachment_helpers import (
    LockedMentorAttachmentScope,
    attachment_batch_view,
    run_with_locked_mentor_attachment_scope,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
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
        return run_with_locked_mentor_attachment_scope(
            self._database,
            account_id,
            batch_id,
            lambda repositories, scope: self._get(
                repositories, scope, account_id, grant, now
            ),
        )

    def _get(
        self,
        repositories: IntelligenceDatabaseRepositories,
        scope: LockedMentorAttachmentScope,
        account_id: str,
        grant: MentorAccessGrant,
        now: datetime,
    ) -> MentorAttachmentBatchView:
        batch = scope.batch
        if (
            batch is None
            or batch.account_id != account_id
            or batch.revoked_at is not None
        ):
            raise MentorAttachmentNotFoundError
        if batch.expires_at <= now and batch.consumed_by_message_id is None:
            raise MentorAttachmentConflictError
        if not scope.session_available:
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

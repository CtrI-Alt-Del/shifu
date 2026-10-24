import re
from datetime import timedelta

from shifu.intelligence.core.domain.entities import MentorAttachmentBatch
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
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
    IdentifierProvider,
    MentorAccessProvider,
)

_SESSION_ID = re.compile(r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')


class CreateMentorAttachmentBatchUseCase:
    _INACTIVITY = timedelta(hours=1)

    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(
        self, account_id: str, session_id: str | None = None
    ) -> MentorAttachmentBatchView:
        if session_id is not None and not _SESSION_ID.fullmatch(session_id):
            raise MentorAttachmentInvalidError(
                'O arquivo não é válido ou não está disponível.'
            )
        batch_id = self._identifier_provider.generate()
        grant = self._access_provider.authorize(account_id, batch_id)
        self._access_provider.assert_current(grant)
        now = self._clock_provider.now()
        batch = MentorAttachmentBatch.create(
            batch_id=batch_id,
            account_id=account_id,
            session_id=session_id,
            now=now,
            expires_at=now + self._INACTIVITY,
        )
        with self._database.transaction() as repositories:
            if (
                session_id is not None
                and repositories.mentor_sessions.find_by_id_for_update(
                    account_id, session_id
                )
                is None
            ):
                raise MentorSessionNotFoundError
            self._access_provider.assert_current(grant)
            repositories.mentor_attachment_batches.add(batch)
            repositories.events.add(
                MentorAttachmentCleanupRequestedEvent(
                    payload=MentorAttachmentCleanupRequestedPayload(
                        account_id=account_id,
                        session_id=None,
                        batch_id=batch_id,
                        deletion_generation=batch.generation,
                    )
                ),
                available_at=batch.expires_at,
            )
            return attachment_batch_view(repositories, batch.id, batch.expires_at)

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import MentorAttachmentNotFoundError
from shifu.intelligence.core.domain.events import (
    MentorAttachmentCleanupRequestedEvent,
    MentorAttachmentCleanupRequestedPayload,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class FailMentorAttachmentUseCase:
    _FAILURE_CODES = frozenset(
        {
            'invalid_file',
            'unreadable_file',
            'analysis_unavailable',
            'attachment_unavailable',
        }
    )

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(
        self,
        attachment_id: str,
        generation: int,
        execution_owner: str,
        failure_code: str,
    ) -> MentorAttachmentStatus:
        if failure_code not in self._FAILURE_CODES:
            raise ValueError('Unsupported mentor attachment failure code')
        with self._database.transaction() as repositories:
            candidate = repositories.mentor_attachments.find_by_id(attachment_id)
            if candidate is None:
                raise MentorAttachmentNotFoundError
            account_id = candidate.account_id
        grant = self._access_provider.authorize(account_id, attachment_id)
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if attachment is None or attachment.account_id != account_id:
                raise MentorAttachmentNotFoundError
            if (
                attachment.generation != generation
                or attachment.status is not MentorAttachmentStatus.PROCESSING
                or attachment.execution_owner != execution_owner
                or attachment.claim_expires_at is None
                or attachment.claim_expires_at <= self._clock_provider.now()
            ):
                return attachment.status
            attachment.transition(MentorAttachmentStatus.FAILED, failure_code)
            repositories.mentor_attachment_chunks.remove_by_attachment_id(attachment_id)
            repositories.mentor_attachments.update(attachment)
            repositories.events.add(
                MentorAttachmentCleanupRequestedEvent(
                    payload=MentorAttachmentCleanupRequestedPayload(
                        account_id=account_id,
                        session_id=None,
                        batch_id=attachment.batch_id,
                        deletion_generation=attachment.generation,
                    )
                )
            )
            self._access_provider.assert_current(grant)
            return attachment.status

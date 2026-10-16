from datetime import timedelta

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class RenewMentorAttachmentClaimUseCase:
    _CLAIM_DURATION = timedelta(minutes=5)

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
        self, attachment_id: str, generation: int, execution_owner: str
    ) -> bool:
        now = self._clock_provider.now()
        with self._database.transaction() as repositories:
            candidate = repositories.mentor_attachments.find_by_id(attachment_id)
            if candidate is None:
                return False
            account_id = candidate.account_id
        grant = self._access_provider.authorize(account_id, attachment_id)
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if (
                attachment is None
                or attachment.account_id != account_id
                or attachment.generation != generation
                or attachment.status is not MentorAttachmentStatus.PROCESSING
                or attachment.execution_owner != execution_owner
                or not attachment.renew_claim(
                    execution_owner, now, now + self._CLAIM_DURATION
                )
            ):
                return False
            batch = repositories.mentor_attachment_batches.find_by_id(
                attachment.batch_id, for_update=True
            )
            if (
                batch is None
                or batch.account_id != account_id
                or batch.revoked_at is not None
                or batch.consumed_by_message_id is not None
                or batch.expires_at <= now
            ):
                return False
            if (
                batch.session_id is not None
                and repositories.mentor_sessions.find_by_id_for_update(
                    account_id, batch.session_id
                )
                is None
            ):
                return False
            repositories.mentor_attachments.update(attachment)
            self._access_provider.assert_current(grant)
            return True

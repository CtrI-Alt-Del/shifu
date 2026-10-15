from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.entities import MentorAttachment
    from shifu.intelligence.core.interfaces import (
        IntelligenceDatabase,
        IntelligenceDatabaseRepositories,
    )
    from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider

from shifu.intelligence.core.domain.errors import MentorAttachmentNotFoundError
from shifu.intelligence.core.domain.events import (
    MentorAttachmentCleanupRequestedEvent,
    MentorAttachmentCleanupRequestedPayload,
)


class RemoveMentorAttachmentUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(self, account_id: str, batch_id: str, attachment_id: str) -> None:
        grant = self._access_provider.authorize(account_id, attachment_id)
        self._access_provider.assert_current(grant)
        now = self._clock_provider.now()
        with self._database.transaction() as repositories:
            batch = repositories.mentor_attachment_batches.find_by_id(
                batch_id, for_update=True
            )
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if (
                batch is None
                or batch.account_id != account_id
                or batch.revoked_at is not None
                or batch.expires_at <= now
                or batch.consumed_by_message_id is not None
                or attachment is None
                or attachment.account_id != account_id
                or attachment.batch_id != batch_id
            ):
                raise MentorAttachmentNotFoundError
            if attachment.status.value == 'removed':
                return
            attachment.revoke()
            repositories.mentor_attachments.update(attachment)
            repositories.events.add(
                MentorAttachmentCleanupRequestedEvent(
                    payload=MentorAttachmentCleanupRequestedPayload(
                        account_id=account_id,
                        session_id=None,
                        batch_id=batch_id,
                        deletion_generation=attachment.generation,
                    )
                )
            )
            self._access_provider.assert_current(grant)


def revoke_session_attachments(
    repositories: IntelligenceDatabaseRepositories,
    access_provider: MentorAccessProvider,
    account_id: str,
    session_id: str,
    now: datetime,
) -> None:
    grant = access_provider.authorize(account_id, session_id)
    access_provider.assert_current(grant)
    attachments: tuple[MentorAttachment, ...] = (
        repositories.mentor_attachments.find_by_session_id(account_id, session_id)
    )
    attachment_changed = False
    for attachment in attachments:
        if attachment.status.value == 'removed':
            continue
        attachment.revoke()
        repositories.mentor_attachments.update(attachment)
        attachment_changed = True
    batches = repositories.mentor_attachment_batches.find_by_session_id(
        account_id, session_id
    )
    batch_changed = False
    for batch in batches:
        if batch.revoked_at is None:
            batch.revoke(now)
            repositories.mentor_attachment_batches.update(batch)
            repositories.events.add(
                MentorAttachmentCleanupRequestedEvent(
                    payload=MentorAttachmentCleanupRequestedPayload(
                        account_id=account_id,
                        session_id=None,
                        batch_id=batch.id,
                        deletion_generation=batch.generation,
                    )
                )
            )
            batch_changed = True
    if attachment_changed and not batch_changed and not batches:
        repositories.events.add(
            MentorAttachmentCleanupRequestedEvent(
                payload=MentorAttachmentCleanupRequestedPayload(
                    account_id=account_id,
                    session_id=session_id,
                    batch_id=None,
                    deletion_generation=max(
                        (attachment.generation for attachment in attachments),
                        default=1,
                    ),
                )
            )
        )
    access_provider.assert_current(grant)

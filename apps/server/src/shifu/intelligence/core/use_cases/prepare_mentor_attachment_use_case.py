from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.entities import (
        MentorAttachment,
        MentorAttachmentBatch,
    )
    from shifu.intelligence.core.interfaces import (
        IntelligenceDatabase,
        IntelligenceDatabaseRepositories,
    )
    from shifu.shared.core.domain.structures import MentorAccessGrant
    from shifu.shared.core.interfaces import (
        ClockProvider,
        FileStorageProvider,
        MentorAccessProvider,
    )

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentNotFoundError,
    MentorAttachmentUnavailableError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import PreparedMentorAttachment
from shifu.intelligence.core.use_cases.mentor_attachment_helpers import (
    LockedMentorAttachmentScope,
    run_with_locked_mentor_attachment_scope,
)


@dataclass(frozen=True)
class _ClaimedAttachment:
    account_id: str
    batch_id: str
    object_key: str
    media_type: str
    checksum: str
    grant: MentorAccessGrant


class PrepareMentorAttachmentUseCase:
    _CLAIM_DURATION = timedelta(minutes=5)

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        storage_provider: FileStorageProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider
        self._storage_provider = storage_provider

    def execute(
        self, attachment_id: str, generation: int, execution_owner: str
    ) -> PreparedMentorAttachment | None:
        if generation < 1 or not execution_owner.strip():
            raise MentorAttachmentConflictError
        claimed = self._claim(attachment_id, generation, execution_owner)
        if claimed is None:
            return None
        content = self._read_claimed(
            attachment_id, generation, execution_owner, claimed
        )
        if content is None:
            return None
        self._access_provider.assert_current(claimed.grant)
        if not self._is_current(attachment_id, generation, execution_owner, claimed):
            return None
        return PreparedMentorAttachment(
            attachment_id=attachment_id,
            generation=generation,
            execution_owner=execution_owner,
            media_type=claimed.media_type,
            content=content,
        )

    def _claim(
        self, attachment_id: str, generation: int, execution_owner: str
    ) -> _ClaimedAttachment | None:
        with self._database.transaction() as repositories:
            candidate = repositories.mentor_attachments.find_by_id(attachment_id)
            if candidate is None:
                raise MentorAttachmentNotFoundError
            account_id = candidate.account_id
            batch_id = candidate.batch_id
        grant = self._access_provider.authorize(account_id, attachment_id)
        self._access_provider.assert_current(grant)
        now = self._clock_provider.now()
        return run_with_locked_mentor_attachment_scope(
            self._database,
            account_id,
            batch_id,
            lambda repositories, scope: self._claim_locked(
                repositories,
                scope,
                account_id,
                generation,
                execution_owner,
                grant,
                now,
            ),
            attachment_id,
        )

    def _claim_locked(
        self,
        repositories: IntelligenceDatabaseRepositories,
        scope: LockedMentorAttachmentScope,
        account_id: str,
        generation: int,
        execution_owner: str,
        grant: MentorAccessGrant,
        now: datetime,
    ) -> _ClaimedAttachment | None:
        attachment = scope.attachment
        batch = scope.batch
        if attachment is None or attachment.account_id != account_id:
            raise MentorAttachmentNotFoundError
        if not self._is_claimable(attachment, generation, execution_owner, now):
            return None
        if batch is None or not self._is_batch_active(batch, account_id, now):
            return None
        if not scope.session_available:
            raise MentorSessionNotFoundError
        attachment.claim(execution_owner, now, now + self._CLAIM_DURATION)
        repositories.mentor_attachments.update(attachment)
        self._access_provider.assert_current(grant)
        return _ClaimedAttachment(
            account_id=account_id,
            batch_id=batch.id,
            object_key=attachment.object_key,
            media_type=attachment.media_type,
            checksum=attachment.checksum,
            grant=grant,
        )

    @staticmethod
    def _is_claimable(
        attachment: MentorAttachment,
        generation: int,
        execution_owner: str,
        now: datetime,
    ) -> bool:
        if attachment.generation != generation or attachment.status not in {
            MentorAttachmentStatus.UPLOADING,
            MentorAttachmentStatus.PROCESSING,
        }:
            return False
        return not (
            attachment.status is MentorAttachmentStatus.PROCESSING
            and attachment.claim_expires_at is not None
            and attachment.claim_expires_at > now
            and attachment.execution_owner != execution_owner
        )

    @staticmethod
    def _is_batch_active(
        batch: MentorAttachmentBatch, account_id: str, now: datetime
    ) -> bool:
        return not (
            batch.account_id != account_id
            or batch.revoked_at is not None
            or batch.consumed_by_message_id is not None
            or batch.expires_at <= now
        )

    def _read_claimed(
        self,
        attachment_id: str,
        generation: int,
        execution_owner: str,
        claimed: _ClaimedAttachment,
    ) -> bytes | None:
        try:
            content = self._storage_provider.read(claimed.object_key)
        except Exception as error:
            self._release_if_current(attachment_id, generation, execution_owner)
            raise MentorAttachmentUnavailableError from error
        if hashlib.sha256(content).hexdigest() != claimed.checksum:
            self._release_if_current(attachment_id, generation, execution_owner)
            raise MentorAttachmentUnavailableError
        return content

    def _is_current(
        self,
        attachment_id: str,
        generation: int,
        execution_owner: str,
        claimed: _ClaimedAttachment,
    ) -> bool:
        now = self._clock_provider.now()
        return run_with_locked_mentor_attachment_scope(
            self._database,
            claimed.account_id,
            claimed.batch_id,
            lambda _repositories, scope: self._is_current_locked(
                scope, generation, execution_owner, claimed, now
            ),
            attachment_id,
        )

    def _is_current_locked(
        self,
        scope: LockedMentorAttachmentScope,
        generation: int,
        execution_owner: str,
        claimed: _ClaimedAttachment,
        now: datetime,
    ) -> bool:
        current = scope.attachment
        batch = scope.batch
        if (
            current is None
            or current.account_id != claimed.account_id
            or current.generation != generation
            or current.status is not MentorAttachmentStatus.PROCESSING
            or current.execution_owner != execution_owner
            or current.claim_expires_at is None
            or current.claim_expires_at <= now
        ):
            return False
        if batch is None or not self._is_batch_active(batch, claimed.account_id, now):
            return False
        return scope.session_available

    def _release_if_current(
        self, attachment_id: str, generation: int, execution_owner: str
    ) -> None:
        with self._database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if (
                attachment is not None
                and attachment.generation == generation
                and attachment.status is MentorAttachmentStatus.PROCESSING
                and attachment.execution_owner == execution_owner
            ):
                attachment.release_claim(execution_owner)
                repositories.mentor_attachments.update(attachment)

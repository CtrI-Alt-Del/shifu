from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.entities import (
        MentorAttachment,
        MentorAttachmentBatch,
    )
    from shifu.intelligence.core.interfaces import IntelligenceDatabase
    from shifu.shared.core.interfaces import ClockProvider, FileStorageProvider

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentUnavailableError,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


class PurgeMentorAttachmentsUseCase:
    """Apply a trusted cleanup fence and retry idempotent private object removal."""

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        storage_provider: FileStorageProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._storage_provider = storage_provider

    def execute(
        self,
        account_id: str,
        session_id: str | None,
        batch_id: str | None,
        deletion_generation: int,
    ) -> int:
        if (
            not account_id.strip()
            or deletion_generation < 1
            or ((session_id is None) == (batch_id is None))
        ):
            raise MentorAttachmentInvalidError
        if batch_id is not None:
            return self._purge_batch_id(account_id, batch_id, deletion_generation)
        if session_id is None:
            raise MentorAttachmentInvalidError
        with self._database.transaction() as repositories:
            batches = repositories.mentor_attachment_batches.find_by_session_id(
                account_id, session_id
            )
        return sum(
            self._purge_batch(account_id, batch, deletion_generation)
            for batch in batches
            if batch.generation == deletion_generation and batch.revoked_at is not None
        )

    def execute_for_deleted_account(self, account_id: str) -> int:
        """Delete all private attachment data after trusted account closure."""
        if not account_id.strip():
            raise MentorAttachmentInvalidError

        with self._database.transaction() as repositories:
            batches = repositories.mentor_attachment_batches.find_by_account_id(
                account_id
            )
            attachments = repositories.mentor_attachments.find_for_cleanup(
                account_id, None, None, removed_only=False
            )
            keys: list[str] = []
            for attachment in attachments:
                if attachment.status is not MentorAttachmentStatus.REMOVED:
                    attachment.revoke()
                    repositories.mentor_attachments.update(attachment)
                repositories.mentor_attachment_chunks.remove_by_attachment_id(
                    attachment.id
                )
                keys.append(attachment.object_key)
                if attachment.preview_key is not None:
                    keys.append(attachment.preview_key)

        self._remove_objects(keys)

        with self._database.transaction() as repositories:
            for attachment in attachments:
                repositories.mentor_attachments.remove(attachment.id)
            for batch in batches:
                repositories.mentor_attachment_batches.remove(batch.id)
        return len(keys)

    def _purge_batch_id(
        self, account_id: str, batch_id: str, deletion_generation: int
    ) -> int:
        with self._database.transaction() as repositories:
            batch = repositories.mentor_attachment_batches.find_by_id(
                batch_id, for_update=True
            )
            if batch is None or batch.account_id != account_id:
                return 0
        return self._purge_batch(account_id, batch, deletion_generation)

    def _purge_batch(
        self,
        account_id: str,
        batch_snapshot: MentorAttachmentBatch,
        deletion_generation: int,
    ) -> int:
        now = self._clock_provider.now()
        with self._database.transaction() as repositories:
            batch = repositories.mentor_attachment_batches.find_by_id(
                batch_snapshot.id, for_update=True
            )
            if batch is None or batch.account_id != account_id:
                return 0
            batch_generation_matches = batch.generation == deletion_generation
            whole_batch = self._is_whole_batch_due(batch, batch_generation_matches, now)
            attachments = repositories.mentor_attachments.find_by_batch_id(batch.id)
            keys: list[str] = []
            for attachment in attachments:
                if not self._should_purge_attachment(
                    attachment, whole_batch, deletion_generation
                ):
                    continue
                if attachment.status is not MentorAttachmentStatus.REMOVED:
                    attachment.revoke()
                    repositories.mentor_attachments.update(attachment)
                repositories.mentor_attachment_chunks.remove_by_attachment_id(
                    attachment.id
                )
                keys.append(attachment.object_key)
                if attachment.preview_key is not None:
                    keys.append(attachment.preview_key)

        self._remove_objects(keys)
        return len(keys)

    def _remove_objects(self, keys: list[str]) -> None:
        for key in keys:
            try:
                self._storage_provider.remove(key)
            except ServiceUnavailableError as error:
                raise MentorAttachmentUnavailableError from error

    @staticmethod
    def _is_whole_batch_due(
        batch: MentorAttachmentBatch, generation_matches: bool, now: datetime
    ) -> bool:
        if not generation_matches:
            return False
        if batch.revoked_at is not None:
            return True
        return batch.consumed_by_message_id is None and batch.expires_at <= now

    @staticmethod
    def _should_purge_attachment(
        attachment: MentorAttachment,
        whole_batch: bool,
        deletion_generation: int,
    ) -> bool:
        if whole_batch:
            return True
        return attachment.generation == deletion_generation and (
            attachment.status is MentorAttachmentStatus.REMOVED
            or attachment.failure_code == 'storage_write_failed'
        )

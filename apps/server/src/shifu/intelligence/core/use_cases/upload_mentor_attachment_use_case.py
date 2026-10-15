from __future__ import annotations

import hashlib
import re
from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

if TYPE_CHECKING:
    from shifu.intelligence.core.interfaces import (
        IntelligenceDatabase,
        IntelligenceDatabaseRepositories,
    )
    from shifu.intelligence.core.interfaces.mentor_attachment_extractor_provider import (
        MentorAttachmentExtractorProvider,
    )
    from shifu.shared.core.domain.structures import MentorAccessGrant
    from shifu.shared.core.interfaces import (
        ClockProvider,
        FileStorageProvider,
        IdentifierProvider,
        MentorAccessProvider,
    )

from shifu.intelligence.core.domain.entities import MentorAttachment
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentInvalidError,
    MentorAttachmentNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    MentorAttachmentCleanupRequestedEvent,
    MentorAttachmentCleanupRequestedPayload,
    MentorAttachmentPreparationRequestedEvent,
    MentorAttachmentPreparationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentFile,
    MentorAttachmentUploadResult,
)
from shifu.intelligence.core.use_cases.mentor_attachment_helpers import (
    attachment_view,
)
from shifu.shared.core.domain.errors import AuthorizationError, ServiceUnavailableError

_MEDIA_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.pdf': 'application/pdf',
    '.json': 'application/json',
    '.csv': 'text/csv',
    '.txt': 'text/plain',
}
_UNSAFE_FILENAME = re.compile(r'[\x00-\x1f\x7f]')
_MAX_FILE_SIZE = 10_000_000
_BATCH_INACTIVITY = timedelta(hours=1)


class UploadMentorAttachmentUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        storage_provider: FileStorageProvider,
        extractor_provider: MentorAttachmentExtractorProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider
        self._access_provider = access_provider
        self._storage_provider = storage_provider
        self._extractor_provider = extractor_provider

    def execute(
        self,
        account_id: str,
        batch_id: str,
        upload_key: str,
        uploaded_file: MentorAttachmentFile,
    ) -> MentorAttachmentUploadResult:
        upload_key = self._validate_upload_key(upload_key)
        filename, media_type, content = self._validate_file(uploaded_file)
        self._extractor_provider.validate(content, media_type)
        checksum = hashlib.sha256(content).hexdigest()
        grant = self._access_provider.authorize(account_id, upload_key)
        self._access_provider.assert_current(grant)
        attachment, created = self._reserve(
            account_id,
            batch_id,
            upload_key,
            filename,
            media_type,
            content,
            checksum,
            grant,
        )
        should_resume = created or (
            attachment.status is MentorAttachmentStatus.UPLOADING
            and attachment.upload_completed_at is None
        )
        if not should_resume:
            return MentorAttachmentUploadResult(
                attachment=attachment_view(attachment), created=False
            )
        try:
            self._storage_provider.put(attachment.object_key, content, media_type)
        except ServiceUnavailableError:
            failed = self._mark_storage_failure(attachment.id, account_id, batch_id)
            return MentorAttachmentUploadResult(
                attachment=attachment_view(failed), created=created
            )
        try:
            result = self._complete_upload(account_id, batch_id, attachment, grant)
            return MentorAttachmentUploadResult(
                attachment=result.attachment, created=created
            )
        except ServiceUnavailableError:
            # Leave private bytes for a retry when the completion transaction fails.
            raise
        except SQLAlchemyError:
            # The reservation transaction rolled back; replay will write these bytes again.
            raise
        except Exception:
            with suppress(ServiceUnavailableError):
                self._storage_provider.remove(attachment.object_key)
            raise

    def _reserve(
        self,
        account_id: str,
        batch_id: str,
        upload_key: str,
        filename: str,
        media_type: str,
        content: bytes,
        checksum: str,
        grant: MentorAccessGrant,
    ) -> tuple[MentorAttachment, bool]:
        now = self._clock_provider.now()
        attachment_id = self._identifier_provider.generate()
        object_key = f'mentor-attachments/{attachment_id}/1/original'
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
            if batch.consumed_by_message_id is not None or batch.expires_at <= now:
                raise MentorAttachmentConflictError
            existing = repositories.mentor_attachments.find_by_upload_key(
                batch_id, upload_key
            )
            if existing is not None:
                if (
                    existing.account_id != account_id
                    or existing.checksum != checksum
                    or existing.filename != filename
                    or existing.media_type != media_type
                ):
                    raise MentorAttachmentConflictError
                return existing, False
            if repositories.mentor_attachments.count_active_in_batch(batch_id) >= 5:
                raise MentorAttachmentConflictError
            attachment = MentorAttachment.create(
                attachment_id=attachment_id,
                account_id=account_id,
                batch_id=batch_id,
                upload_key=upload_key,
                filename=filename,
                media_type=media_type,
                size_bytes=len(content),
                checksum=checksum,
                object_key=object_key,
                now=now,
            )
            self._access_provider.assert_current(grant)
            repositories.mentor_attachments.add(attachment)
            renewed_expiry = now + _BATCH_INACTIVITY
            if renewed_expiry > batch.expires_at:
                batch.renew(renewed_expiry)
                repositories.mentor_attachment_batches.update(batch)
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
        return attachment, True

    def _mark_storage_failure(
        self, attachment_id: str, account_id: str, batch_id: str
    ) -> MentorAttachment:
        with self._database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(
                attachment_id, for_update=True
            )
            if attachment is None:
                raise MentorAttachmentNotFoundError
            if (
                attachment.generation == 1
                and attachment.status is MentorAttachmentStatus.UPLOADING
            ):
                attachment.transition(
                    MentorAttachmentStatus.FAILED, 'storage_write_failed'
                )
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
            return attachment

    def _complete_upload(
        self,
        account_id: str,
        batch_id: str,
        attachment: MentorAttachment,
        grant: MentorAccessGrant,
    ) -> MentorAttachmentUploadResult:
        access_error: AuthorizationError | None = None
        with self._database.transaction() as repositories:
            current = repositories.mentor_attachments.find_by_id(
                attachment.id, for_update=True
            )
            if (
                current is None
                or current.generation != 1
                or current.status is MentorAttachmentStatus.REMOVED
            ):
                raise MentorAttachmentConflictError
            batch = repositories.mentor_attachment_batches.find_by_id(
                batch_id, for_update=True
            )
            if (
                batch is None
                or batch.account_id != account_id
                or batch.revoked_at is not None
                or batch.consumed_by_message_id is not None
                or batch.expires_at <= self._clock_provider.now()
                or (
                    batch.session_id is not None
                    and repositories.mentor_sessions.find_by_id_for_update(
                        account_id, batch.session_id
                    )
                    is None
                )
            ):
                return self._revoke_and_queue(
                    repositories, current, account_id, batch_id
                )
            try:
                self._access_provider.assert_current(grant)
            except AuthorizationError as error:
                self._revoke_and_queue(repositories, current, account_id, batch_id)
                access_error = error
            else:
                if current.upload_completed_at is None:
                    current.mark_upload_completed(self._clock_provider.now())
                    repositories.mentor_attachments.update(current)
                    repositories.events.add(
                        MentorAttachmentPreparationRequestedEvent(
                            payload=MentorAttachmentPreparationRequestedPayload(
                                attachment_id=current.id,
                                generation=current.generation,
                            )
                        )
                    )
        if access_error is not None:
            raise access_error
        return MentorAttachmentUploadResult(
            attachment=attachment_view(current), created=True
        )

    @staticmethod
    def _revoke_and_queue(
        repositories: IntelligenceDatabaseRepositories,
        attachment: MentorAttachment,
        account_id: str,
        batch_id: str,
    ) -> MentorAttachmentUploadResult:
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
        return MentorAttachmentUploadResult(
            attachment=attachment_view(attachment), created=True
        )

    @staticmethod
    def _validate_file(
        uploaded_file: MentorAttachmentFile,
    ) -> tuple[str, str, bytes]:
        if type(uploaded_file.content) is not bytes:
            raise MentorAttachmentInvalidError
        content = uploaded_file.content
        if not 0 < len(content) <= _MAX_FILE_SIZE:
            raise MentorAttachmentInvalidError
        filename = uploaded_file.filename.strip().replace('\\', '/').rsplit('/', 1)[-1]
        if not filename or len(filename) > 255 or _UNSAFE_FILENAME.search(filename):
            raise MentorAttachmentInvalidError
        extension = (
            '.' + filename.rsplit('.', 1)[-1].casefold() if '.' in filename else ''
        )
        media_type = _MEDIA_TYPES.get(extension)
        declared = uploaded_file.media_type.split(';', maxsplit=1)[0].strip().lower()
        if media_type is None or declared != media_type:
            raise MentorAttachmentInvalidError
        return filename, media_type, content

    @staticmethod
    def _validate_upload_key(upload_key: str) -> str:
        try:
            parsed = UUID(upload_key)
        except (ValueError, AttributeError) as error:
            raise MentorAttachmentInvalidError from error
        if parsed.version != 4 or str(parsed) != upload_key.lower():
            raise MentorAttachmentInvalidError
        return str(parsed)

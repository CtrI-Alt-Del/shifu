from __future__ import annotations

from typing import TYPE_CHECKING

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentInvalidError,
)
from shifu.shared.core.domain.entities import entity

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.structures.mentor_attachment_extraction import (
        MentorAttachmentExtraction,
    )

_ALLOWED_TRANSITIONS: dict[
    MentorAttachmentStatus, frozenset[MentorAttachmentStatus]
] = {
    MentorAttachmentStatus.UPLOADING: frozenset(
        {
            MentorAttachmentStatus.PROCESSING,
            MentorAttachmentStatus.FAILED,
            MentorAttachmentStatus.REMOVED,
        }
    ),
    MentorAttachmentStatus.PROCESSING: frozenset(
        {
            MentorAttachmentStatus.READY,
            MentorAttachmentStatus.PARTIAL,
            MentorAttachmentStatus.FAILED,
            MentorAttachmentStatus.REMOVED,
        }
    ),
    MentorAttachmentStatus.READY: frozenset({MentorAttachmentStatus.REMOVED}),
    MentorAttachmentStatus.PARTIAL: frozenset({MentorAttachmentStatus.REMOVED}),
    MentorAttachmentStatus.FAILED: frozenset({MentorAttachmentStatus.REMOVED}),
    MentorAttachmentStatus.REMOVED: frozenset(),
}


@entity
class MentorAttachment:
    id: str
    account_id: str
    batch_id: str
    session_id: str | None
    message_id: str | None
    generation: int
    upload_key: str
    filename: str
    media_type: str
    size_bytes: int
    checksum: str
    object_key: str
    preview_key: str | None
    status: MentorAttachmentStatus
    failure_code: str | None
    created_at: datetime
    execution_owner: str | None
    claim_expires_at: datetime | None
    analyzed_pages: tuple[int, ...]
    illegible_pages: tuple[int, ...]
    uninterpreted_pages: tuple[int, ...]
    upload_completed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        attachment_id: str,
        account_id: str,
        batch_id: str,
        upload_key: str,
        filename: str,
        media_type: str,
        size_bytes: int,
        checksum: str,
        object_key: str,
        now: datetime,
    ) -> MentorAttachment:
        if (
            not attachment_id.strip()
            or not account_id.strip()
            or not batch_id.strip()
            or not upload_key.strip()
            or not filename.strip()
            or filename != filename.replace('\\', '/').rsplit('/', 1)[-1]
            or not media_type.strip()
            or not 0 < size_bytes <= 10_000_000
            or len(checksum) != 64
            or any(character not in '0123456789abcdef' for character in checksum)
            or not object_key.strip()
        ):
            raise MentorAttachmentInvalidError
        return cls(
            id=attachment_id,
            account_id=account_id,
            batch_id=batch_id,
            session_id=None,
            message_id=None,
            generation=1,
            upload_key=upload_key,
            filename=filename,
            media_type=media_type,
            size_bytes=size_bytes,
            checksum=checksum,
            object_key=object_key,
            preview_key=None,
            status=MentorAttachmentStatus.UPLOADING,
            failure_code=None,
            created_at=now,
            execution_owner=None,
            claim_expires_at=None,
            analyzed_pages=(),
            illegible_pages=(),
            uninterpreted_pages=(),
            upload_completed_at=None,
        )

    def mark_upload_completed(self, now: datetime) -> None:
        if self.status is not MentorAttachmentStatus.UPLOADING:
            raise MentorAttachmentConflictError
        self.upload_completed_at = now

    def bind(self, session_id: str, message_id: str) -> None:
        if self.status not in {
            MentorAttachmentStatus.READY,
            MentorAttachmentStatus.PARTIAL,
        }:
            raise MentorAttachmentConflictError
        if self.message_id is not None:
            if self.session_id == session_id and self.message_id == message_id:
                return
            raise MentorAttachmentConflictError
        if not session_id.strip() or not message_id.strip():
            raise MentorAttachmentInvalidError
        self.session_id = session_id
        self.message_id = message_id

    def transition(
        self,
        status: MentorAttachmentStatus,
        failure_code: str | None = None,
    ) -> None:
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            if status == self.status and self.failure_code == failure_code:
                return
            raise MentorAttachmentConflictError
        self.status = status
        self.failure_code = failure_code
        if status != MentorAttachmentStatus.PROCESSING:
            self.execution_owner = None
            self.claim_expires_at = None

    def claim(self, execution_owner: str, now: datetime, expires_at: datetime) -> None:
        if self.status not in {
            MentorAttachmentStatus.UPLOADING,
            MentorAttachmentStatus.PROCESSING,
        }:
            raise MentorAttachmentConflictError
        if (
            self.execution_owner is not None
            and self.claim_expires_at is not None
            and self.claim_expires_at > now
            and self.execution_owner != execution_owner
        ):
            raise MentorAttachmentConflictError
        if not execution_owner.strip() or expires_at <= now:
            raise MentorAttachmentInvalidError
        self.status = MentorAttachmentStatus.PROCESSING
        self.execution_owner = execution_owner
        self.claim_expires_at = expires_at
        self.failure_code = None

    def renew_claim(
        self, execution_owner: str, now: datetime, expires_at: datetime
    ) -> bool:
        if (
            self.status != MentorAttachmentStatus.PROCESSING
            or self.execution_owner != execution_owner
            or self.claim_expires_at is None
            or self.claim_expires_at <= now
            or expires_at <= self.claim_expires_at
        ):
            return False
        self.claim_expires_at = expires_at
        return True

    def release_claim(self, execution_owner: str) -> None:
        if self.execution_owner == execution_owner:
            self.execution_owner = None
            self.claim_expires_at = None

    def apply_extraction(
        self,
        extraction: MentorAttachmentExtraction,
        status: MentorAttachmentStatus,
        failure_code: str | None = None,
    ) -> None:
        if status not in {MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL}:
            raise MentorAttachmentInvalidError
        if status == MentorAttachmentStatus.READY and (
            extraction.illegible_pages or extraction.uninterpreted_pages
        ):
            raise MentorAttachmentInvalidError
        self.analyzed_pages = extraction.analyzed_pages
        self.illegible_pages = extraction.illegible_pages
        self.uninterpreted_pages = extraction.uninterpreted_pages
        self.status = status
        self.failure_code = failure_code
        self.execution_owner = None
        self.claim_expires_at = None

    def fail_extraction(
        self, extraction: MentorAttachmentExtraction, failure_code: str
    ) -> None:
        if self.status != MentorAttachmentStatus.PROCESSING or not failure_code.strip():
            raise MentorAttachmentConflictError
        self.analyzed_pages = extraction.analyzed_pages
        self.illegible_pages = extraction.illegible_pages
        self.uninterpreted_pages = extraction.uninterpreted_pages
        self.status = MentorAttachmentStatus.FAILED
        self.failure_code = failure_code
        self.execution_owner = None
        self.claim_expires_at = None

    def revoke(self) -> None:
        if self.status != MentorAttachmentStatus.REMOVED:
            self.status = MentorAttachmentStatus.REMOVED
            self.generation += 1
            self.execution_owner = None
            self.claim_expires_at = None

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentInvalidError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentBatchView,
    MentorAttachmentView,
)
from shifu.intelligence.core.interfaces.intelligence_database import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)

_LOCK_ATTEMPTS = 3


@dataclass(frozen=True)
class LockedMentorAttachmentScope:
    batch: MentorAttachmentBatch | None
    attachment: MentorAttachment | None
    session_available: bool


def run_with_locked_mentor_attachment_scope[T](
    database: IntelligenceDatabase,
    account_id: str,
    batch_id: str,
    action: Callable[
        [IntelligenceDatabaseRepositories, LockedMentorAttachmentScope], T
    ],
    attachment_id: str | None = None,
) -> T:
    """Run `action` holding locks in the global order session, batch, attachment.

    The batch session binding is only known after reading the batch, so it is
    peeked in a separate transaction. Binding is one-way (unbound to bound); when
    the locked batch no longer matches the peek, the transaction restarts instead
    of locking the session after the batch.
    """
    for _ in range(_LOCK_ATTEMPTS):
        with database.transaction() as repositories:
            peeked = repositories.mentor_attachment_batches.find_by_id(batch_id)
        peeked_session_id = peeked.session_id if peeked is not None else None
        with database.transaction() as repositories:
            session_available = (
                peeked_session_id is None
                or repositories.mentor_sessions.find_by_id_for_update(
                    account_id, peeked_session_id
                )
                is not None
            )
            batch = repositories.mentor_attachment_batches.find_by_id(
                batch_id, for_update=True
            )
            if (batch.session_id if batch is not None else None) != peeked_session_id:
                continue
            attachment = (
                repositories.mentor_attachments.find_by_id(
                    attachment_id, for_update=True
                )
                if attachment_id is not None
                else None
            )
            if attachment is not None and attachment.batch_id != batch_id:
                continue
            return action(
                repositories,
                LockedMentorAttachmentScope(batch, attachment, session_available),
            )
    raise MentorAttachmentConflictError


def attachment_view(attachment: MentorAttachment) -> MentorAttachmentView:
    return MentorAttachmentView(
        attachment_id=attachment.id,
        filename=attachment.filename,
        media_type=attachment.media_type,
        size_bytes=attachment.size_bytes,
        status=attachment.status,
        failure_code=attachment.failure_code,
        analyzed_pages=attachment.analyzed_pages,
        illegible_pages=attachment.illegible_pages,
        uninterpreted_pages=attachment.uninterpreted_pages,
    )


def attachment_batch_view(
    repositories: IntelligenceDatabaseRepositories,
    batch_id: str,
    expires_at: datetime,
) -> MentorAttachmentBatchView:
    return MentorAttachmentBatchView(
        batch_id=batch_id,
        expires_at=expires_at,
        attachments=tuple(
            attachment_view(attachment)
            for attachment in repositories.mentor_attachments.find_by_batch_id(batch_id)
        ),
    )


def selected_attachments(
    repositories: IntelligenceDatabaseRepositories,
    *,
    account_id: str,
    batch_id: str | None,
    session_id: str,
    attachment_ids: tuple[str, ...],
    now: datetime,
    allow_unbound_session: bool = False,
) -> tuple[MentorAttachment, ...]:
    if not attachment_ids:
        if batch_id is not None:
            raise MentorAttachmentInvalidError
        return ()
    if (
        batch_id is None
        or len(attachment_ids) > 5
        or len(set(attachment_ids)) != len(attachment_ids)
    ):
        raise MentorAttachmentInvalidError
    batch = repositories.mentor_attachment_batches.find_by_id(batch_id, for_update=True)
    if (
        batch is None
        or batch.account_id != account_id
        or batch.revoked_at is not None
        or batch.expires_at <= now
        or batch.consumed_by_message_id is not None
        or (
            batch.session_id != session_id
            and not (allow_unbound_session and batch.session_id is None)
        )
    ):
        raise MentorAttachmentConflictError
    attachments = tuple(
        repositories.mentor_attachments.find_by_id(attachment_id, for_update=True)
        for attachment_id in attachment_ids
    )
    if any(
        attachment is None
        or attachment.account_id != account_id
        or attachment.batch_id != batch_id
        or attachment.status
        not in {MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL}
        or attachment.message_id is not None
        for attachment in attachments
    ):
        raise MentorAttachmentConflictError
    return tuple(attachment for attachment in attachments if attachment is not None)


def attachment_fingerprint_values(
    repositories: IntelligenceDatabaseRepositories,
    account_id: str,
    batch_id: str | None,
    attachment_ids: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    if not attachment_ids:
        if batch_id is not None:
            raise MentorAttachmentInvalidError
        return ()
    if (
        batch_id is None
        or len(attachment_ids) > 5
        or len(set(attachment_ids)) != len(attachment_ids)
    ):
        raise MentorAttachmentInvalidError
    attachments = tuple(
        repositories.mentor_attachments.find_by_id(attachment_id)
        for attachment_id in attachment_ids
    )
    if any(
        attachment is None
        or attachment.account_id != account_id
        or attachment.batch_id != batch_id
        for attachment in attachments
    ):
        raise MentorAttachmentConflictError
    return tuple(
        (attachment.id, attachment.checksum)
        for attachment in attachments
        if attachment is not None
    )

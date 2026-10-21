from datetime import UTC, datetime, timedelta

import pytest

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
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
    MentorAttachmentSource,
)

_NOW = datetime(2026, 10, 15, tzinfo=UTC)
_EXECUTION_END = _NOW + timedelta(minutes=5)


def _attachment() -> MentorAttachment:
    return MentorAttachment.create(
        attachment_id='01K7DFR35H18HZM5Q8R6KV0W2B',
        account_id='account-1',
        batch_id='01K7DFR35H18HZM5Q8R6KV0W2C',
        upload_key='upload-1',
        filename='lesson.pdf',
        media_type='application/pdf',
        size_bytes=100,
        checksum='a' * 64,
        object_key='private/lesson.pdf',
        now=_NOW,
    )


def _chunk(
    *, chunk_id: str = 'chunk-1', page_number: int | None = 1, content: str = 'Lesson'
) -> MentorAttachmentChunk:
    return MentorAttachmentChunk(
        chunk_id=chunk_id,
        attachment_id='01K7DFR35H18HZM5Q8R6KV0W2B',
        generation=1,
        page_number=page_number,
        locator='page 1',
        content=content,
    )


@pytest.mark.parametrize(
    ('changes',),
    [
        ({'attachment_id': ' '},),
        ({'account_id': ' '},),
        ({'batch_id': ' '},),
        ({'upload_key': ' '},),
        ({'filename': ' '},),
        ({'filename': '../lesson.pdf'},),
        ({'media_type': ' '},),
        ({'size_bytes': 0},),
        ({'size_bytes': 10_000_001},),
        ({'checksum': 'a' * 63},),
        ({'checksum': 'g' * 64},),
        ({'object_key': ' '},),
    ],
)
def test_attachment_creation_rejects_invalid_upload_metadata(
    changes: dict[str, object],
) -> None:
    values: dict[str, object] = {
        'attachment_id': '01K7DFR35H18HZM5Q8R6KV0W2B',
        'account_id': 'account-1',
        'batch_id': '01K7DFR35H18HZM5Q8R6KV0W2C',
        'upload_key': 'upload-1',
        'filename': 'lesson.pdf',
        'media_type': 'application/pdf',
        'size_bytes': 100,
        'checksum': 'a' * 64,
        'object_key': 'private/lesson.pdf',
        'now': _NOW,
    }
    values.update(changes)

    with pytest.raises(MentorAttachmentInvalidError):
        MentorAttachment.create(**values)  # type: ignore[arg-type]


def test_attachment_binding_is_idempotent_only_for_the_same_message() -> None:
    attachment = _attachment()
    attachment.transition(MentorAttachmentStatus.PROCESSING)
    attachment.transition(MentorAttachmentStatus.READY)

    attachment.bind('session-1', 'message-1')
    attachment.bind('session-1', 'message-1')

    with pytest.raises(MentorAttachmentConflictError):
        attachment.bind('session-2', 'message-2')


@pytest.mark.parametrize(
    ('session_id', 'message_id'),
    [(' ', 'message-1'), ('session-1', ' ')],
)
def test_attachment_binding_rejects_blank_identifiers(
    session_id: str, message_id: str
) -> None:
    attachment = _attachment()
    attachment.transition(MentorAttachmentStatus.PROCESSING)
    attachment.transition(MentorAttachmentStatus.PARTIAL)

    with pytest.raises(MentorAttachmentInvalidError):
        attachment.bind(session_id, message_id)


def test_attachment_binding_requires_a_ready_or_partial_state() -> None:
    with pytest.raises(MentorAttachmentConflictError):
        _attachment().bind('session-1', 'message-1')


def test_attachment_claim_renewal_and_release_are_owner_scoped() -> None:
    attachment = _attachment()
    attachment.claim('worker-1', _NOW, _EXECUTION_END)

    with pytest.raises(MentorAttachmentConflictError):
        attachment.claim('worker-2', _NOW, _EXECUTION_END)

    assert not attachment.renew_claim('worker-2', _NOW, _NOW + timedelta(minutes=10))
    assert not attachment.renew_claim('worker-1', _NOW, _EXECUTION_END)
    assert attachment.renew_claim('worker-1', _NOW, _NOW + timedelta(minutes=10))

    attachment.release_claim('worker-2')
    assert attachment.execution_owner == 'worker-1'
    attachment.release_claim('worker-1')
    assert attachment.execution_owner is None


def test_attachment_claim_rejects_invalid_owner_and_expiration() -> None:
    for owner, expiry in (
        (' ', _EXECUTION_END),
        ('worker-1', _NOW),
    ):
        with pytest.raises(MentorAttachmentInvalidError):
            _attachment().claim(owner, _NOW, expiry)


def test_attachment_extraction_records_partial_pages_and_revokes_once() -> None:
    attachment = _attachment()
    attachment.claim('worker-1', _NOW, _EXECUTION_END)
    extraction = MentorAttachmentExtraction(
        chunks=(_chunk(),),
        analyzed_pages=(1,),
        illegible_pages=(2,),
        uninterpreted_pages=(),
        limitations=('Page 2 could not be read.',),
    )

    with pytest.raises(MentorAttachmentInvalidError):
        attachment.apply_extraction(extraction, MentorAttachmentStatus.READY)

    attachment.apply_extraction(extraction, MentorAttachmentStatus.PARTIAL)
    assert attachment.analyzed_pages == (1,)
    assert attachment.illegible_pages == (2,)
    assert attachment.execution_owner is None
    attachment.revoke()
    assert attachment.status is MentorAttachmentStatus.REMOVED
    assert attachment.generation == 2
    attachment.revoke()
    assert attachment.generation == 2


def test_attachment_failure_and_transition_guards_are_explicit() -> None:
    attachment = _attachment()
    extraction = MentorAttachmentExtraction(
        chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
    )

    with pytest.raises(MentorAttachmentConflictError):
        attachment.fail_extraction(extraction, 'extraction_failed')
    with pytest.raises(MentorAttachmentConflictError):
        attachment.transition(MentorAttachmentStatus.READY)

    attachment.claim('worker-1', _NOW, _EXECUTION_END)
    with pytest.raises(MentorAttachmentConflictError):
        attachment.fail_extraction(extraction, ' ')
    attachment.fail_extraction(extraction, 'extraction_failed')
    assert attachment.status is MentorAttachmentStatus.FAILED
    assert attachment.failure_code == 'extraction_failed'


def test_attachment_batch_lifecycle_is_idempotent_and_monotonic() -> None:
    batch = MentorAttachmentBatch.create(
        batch_id='01K7DFR35H18HZM5Q8R6KV0W2D',
        account_id='account-1',
        session_id=None,
        now=_NOW,
        expires_at=_NOW + timedelta(hours=1),
    )
    batch.renew(_NOW + timedelta(hours=2))
    assert batch.generation == 2

    batch.consume('message-1')
    batch.consume('message-1')
    with pytest.raises(MentorAttachmentConflictError):
        batch.consume('message-2')
    with pytest.raises(MentorAttachmentConflictError):
        batch.renew(_NOW + timedelta(hours=3))

    batch.revoke(_NOW)
    batch.revoke(_NOW + timedelta(minutes=1))
    assert batch.generation == 3


@pytest.mark.parametrize(
    ('batch_id', 'account_id', 'session_id', 'expires_at'),
    [
        (' ', 'account-1', None, _NOW + timedelta(hours=1)),
        ('batch-1', ' ', None, _NOW + timedelta(hours=1)),
        ('batch-1', 'account-1', ' ', _NOW + timedelta(hours=1)),
        ('batch-1', 'account-1', None, _NOW),
    ],
)
def test_batch_creation_rejects_invalid_scope_or_expiration(
    batch_id: str,
    account_id: str,
    session_id: str | None,
    expires_at: datetime,
) -> None:
    with pytest.raises(MentorAttachmentInvalidError):
        MentorAttachmentBatch.create(
            batch_id=batch_id,
            account_id=account_id,
            session_id=session_id,
            now=_NOW,
            expires_at=expires_at,
        )


def test_attachment_structures_reject_invalid_pages_and_duplicate_chunks() -> None:
    with pytest.raises(MentorAttachmentInvalidError):
        _chunk(page_number=0)
    with pytest.raises(MentorAttachmentInvalidError):
        _chunk(content=' ')
    with pytest.raises(MentorAttachmentInvalidError):
        MentorAttachmentSource(
            attachment_id='attachment-1',
            chunk_id='chunk-1',
            page_number=0,
            locator='page 1',
        )

    with pytest.raises(MentorAttachmentInvalidError):
        MentorAttachmentExtraction(
            chunks=(),
            analyzed_pages=(1,),
            illegible_pages=(1,),
            uninterpreted_pages=(),
        )
    with pytest.raises(MentorAttachmentInvalidError):
        MentorAttachmentExtraction(
            chunks=(_chunk(), _chunk()),
            analyzed_pages=(1,),
            illegible_pages=(),
            uninterpreted_pages=(),
        )

    MentorAttachmentExtraction(
        chunks=(_chunk(),),
        analyzed_pages=(1,),
        illegible_pages=(),
        uninterpreted_pages=(),
    )

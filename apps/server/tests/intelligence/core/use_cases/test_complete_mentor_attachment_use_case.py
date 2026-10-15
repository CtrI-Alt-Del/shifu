from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import call, create_autospec

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentNotFoundError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentChunksRepository,
    MentorAttachmentsRepository,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import CompleteMentorAttachmentUseCase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_SESSION_ID = '01JSESSION000000000000000001'
_EXECUTION_OWNER = 'preparation-worker'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)
_Harness = tuple[CompleteMentorAttachmentUseCase, dict[str, Any]]


def _extraction(*, generation: int = 1) -> MentorAttachmentExtraction:
    return MentorAttachmentExtraction(
        chunks=(
            MentorAttachmentChunk(
                chunk_id='01JCHUNK0000000000000000001',
                attachment_id=_ATTACHMENT_ID,
                generation=generation,
                page_number=None,
                locator='chars:1-18#1',
                content='conteudo educacional',
            ),
        ),
        analyzed_pages=(),
        illegible_pages=(),
        uninterpreted_pages=(),
    )


@pytest.fixture
def harness() -> _Harness:
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, _NOW, _NOW + timedelta(hours=1)
    )
    attachment = MentorAttachment.create(
        _ATTACHMENT_ID,
        _ACCOUNT_ID,
        _BATCH_ID,
        'upload-key',
        'notes.txt',
        'text/plain',
        20,
        'a' * 64,
        f'mentor-attachments/{_ATTACHMENT_ID}/1/original',
        _NOW,
    )
    attachment.claim(
        _EXECUTION_OWNER, _NOW - timedelta(minutes=1), _NOW + timedelta(minutes=4)
    )
    database = create_autospec(IntelligenceDatabase, instance=True)
    repositories = create_autospec(IntelligenceDatabaseRepositories, instance=True)
    repositories.mentor_attachments = create_autospec(
        MentorAttachmentsRepository, instance=True
    )
    repositories.mentor_attachment_batches = create_autospec(
        MentorAttachmentBatchesRepository, instance=True
    )
    repositories.mentor_attachment_chunks = create_autospec(
        MentorAttachmentChunksRepository, instance=True
    )
    repositories.mentor_sessions = create_autospec(
        MentorSessionsRepository, instance=True
    )
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.mentor_attachments.find_by_id.return_value = attachment
    repositories.mentor_attachment_batches.find_by_id.return_value = batch
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = _NOW
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='revision-1',
        operation_key=_ATTACHMENT_ID,
    )
    subject = CompleteMentorAttachmentUseCase(database, clock, access)
    return subject, {
        'attachment': attachment,
        'batch': batch,
        'repositories': repositories,
        'access': access,
    }


def test_complete_persists_valid_chunks_and_clears_the_claim(harness: _Harness) -> None:
    subject, dependencies = harness
    extraction = _extraction()

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, extraction)

    attachment = dependencies['attachment']
    assert status is MentorAttachmentStatus.READY
    assert attachment.status is MentorAttachmentStatus.READY
    assert attachment.execution_owner is None
    assert attachment.claim_expires_at is None
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.add_many.assert_called_once_with(extraction.chunks)
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [call(_ATTACHMENT_ID), call(_ATTACHMENT_ID, for_update=True)]
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.assert_called_once_with(
        _BATCH_ID, for_update=True
    )
    dependencies['access'].authorize.assert_called_once_with(
        _ACCOUNT_ID, _ATTACHMENT_ID
    )
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


@pytest.mark.parametrize(
    'generation,owner', [(2, _EXECUTION_OWNER), (1, 'stale-worker')]
)
def test_complete_ignores_stale_generation_or_execution_owner(
    harness: _Harness, generation: int, owner: str
) -> None:
    subject, dependencies = harness

    status = subject.execute(_ATTACHMENT_ID, generation, owner, _extraction())

    assert status is MentorAttachmentStatus.PROCESSING
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


@pytest.mark.parametrize('batch_state', ['revoked', 'expired', 'consumed'])
def test_complete_revokes_attachment_when_batch_is_not_active(
    harness: _Harness, batch_state: str
) -> None:
    subject, dependencies = harness
    batch = dependencies['batch']
    if batch_state == 'revoked':
        batch.revoke(_NOW)
    elif batch_state == 'expired':
        batch.expires_at = _NOW
    else:
        batch.consume('message-id')

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    attachment = dependencies['attachment']
    assert status is MentorAttachmentStatus.REMOVED
    assert attachment.generation == 2
    assert attachment.execution_owner is None
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


def test_complete_revokes_attachment_when_its_session_is_missing(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['batch'].session_id = _SESSION_ID
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = None

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    assert status is MentorAttachmentStatus.REMOVED
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.assert_called_once_with(
        _ACCOUNT_ID, _SESSION_ID
    )
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        dependencies['attachment']
    )
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


def test_complete_accepts_existing_bound_session(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['batch'].session_id = _SESSION_ID
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    assert status is MentorAttachmentStatus.READY
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.assert_called_once_with(
        _ACCOUNT_ID, _SESSION_ID
    )


def test_complete_rejects_chunks_from_another_generation(harness: _Harness) -> None:
    subject, dependencies = harness

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction(generation=2))

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


def test_complete_does_not_write_after_authorization_is_revoked(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['access'].assert_current.side_effect = PermissionError

    with pytest.raises(PermissionError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


@pytest.mark.parametrize('claim_state', ['expired', 'missing', 'ready'])
def test_complete_ignores_expired_or_non_processing_claims(
    harness: _Harness, claim_state: str
) -> None:
    subject, dependencies = harness
    attachment = dependencies['attachment']
    if claim_state == 'expired':
        attachment.claim_expires_at = _NOW
    elif claim_state == 'missing':
        attachment.claim_expires_at = None
    else:
        attachment.status = MentorAttachmentStatus.READY

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    assert status is attachment.status
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


@pytest.mark.parametrize(
    'batch_state',
    ['missing', 'foreign'],
)
def test_complete_revokes_attachment_when_batch_is_missing_or_foreign(
    harness: _Harness, batch_state: str
) -> None:
    subject, dependencies = harness
    if batch_state == 'missing':
        dependencies[
            'repositories'
        ].mentor_attachment_batches.find_by_id.return_value = None
    else:
        dependencies['batch'].account_id = '01JOTHERACCOUNT00000000000001'

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    assert status is MentorAttachmentStatus.REMOVED
    dependencies['repositories'].mentor_attachments.update.assert_called_once()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


def test_complete_fails_unreadable_extraction_without_chunks(harness: _Harness) -> None:
    subject, dependencies = harness

    status = subject.execute(
        _ATTACHMENT_ID, 1, _EXECUTION_OWNER, replace(_extraction(), chunks=())
    )

    attachment = dependencies['attachment']
    assert status is MentorAttachmentStatus.FAILED
    assert attachment.failure_code == 'unreadable_file'
    assert attachment.analyzed_pages == ()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


def test_complete_marks_extraction_limitations_as_partial(harness: _Harness) -> None:
    subject, dependencies = harness
    extraction = replace(_extraction(), limitations=('extracted_text_truncated',))

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, extraction)

    assert status is MentorAttachmentStatus.PARTIAL
    assert dependencies['attachment'].status is MentorAttachmentStatus.PARTIAL
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.add_many.assert_called_once_with(extraction.chunks)


@pytest.mark.parametrize(
    'media_type,page_number,analyzed_pages,chunk_attachment',
    [
        ('text/plain', 1, (), _ATTACHMENT_ID),
        ('text/plain', None, (), '01JOTHERATTACHMENT0000000001'),
        ('application/pdf', None, (), _ATTACHMENT_ID),
        ('image/png', 2, (1, 2), _ATTACHMENT_ID),
    ],
)
def test_complete_rejects_chunks_outside_attachment_page_scope(
    harness: _Harness,
    media_type: str,
    page_number: int | None,
    analyzed_pages: tuple[int, ...],
    chunk_attachment: str,
) -> None:
    subject, dependencies = harness
    dependencies['attachment'].media_type = media_type
    extraction = _extraction()
    chunk = replace(
        extraction.chunks[0],
        page_number=page_number,
        attachment_id=chunk_attachment,
    )
    extraction = replace(extraction, chunks=(chunk,), analyzed_pages=analyzed_pages)

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, extraction)

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


def test_complete_rejects_missing_attachment_before_authorization(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = None

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    dependencies['access'].authorize.assert_not_called()


def test_complete_rejects_attachment_whose_account_changed(harness: _Harness) -> None:
    subject, dependencies = harness
    attachment = dependencies['attachment']
    foreign_attachment = replace(attachment, account_id='01JOTHERACCOUNT00000000000001')
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = [
        attachment,
        foreign_attachment,
    ]

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, _extraction())

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_chunks.add_many.assert_not_called()


@pytest.mark.parametrize('page_field', ['illegible_pages', 'uninterpreted_pages'])
def test_complete_marks_each_unreadable_page_category_as_partial(
    harness: _Harness, page_field: str
) -> None:
    subject, dependencies = harness
    extraction = replace(_extraction(), **{page_field: (1,)})

    status = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, extraction)

    assert status is MentorAttachmentStatus.PARTIAL
    assert dependencies['attachment'].status is MentorAttachmentStatus.PARTIAL

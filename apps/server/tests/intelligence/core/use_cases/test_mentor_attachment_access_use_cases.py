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
    MentorAttachmentConflictError,
    MentorAttachmentInvalidError,
    MentorAttachmentNotFoundError,
    MentorAttachmentUnavailableError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import MentorAttachmentChunk
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentChunksRepository,
    MentorAttachmentsRepository,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import (
    CreateMentorAttachmentBatchUseCase,
    GetMentorAttachmentBatchUseCase,
    GetMentorAttachmentContextUseCase,
    ReadMentorAttachmentFileUseCase,
    RemoveMentorAttachmentUseCase,
)
from shifu.intelligence.core.use_cases.remove_mentor_attachment_use_case import (
    revoke_session_attachments,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_OTHER_ACCOUNT_ID = '01JOTHERACCOUNT00000000000001'
_SESSION_ID = '01JSESSION000000000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_MESSAGE_ID = '01JMESSAGE000000000000000001'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)


def _batch(*, session_id: str | None = None) -> MentorAttachmentBatch:
    return MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, session_id, _NOW, _NOW + timedelta(minutes=30)
    )


def _attachment(
    *,
    status: MentorAttachmentStatus = MentorAttachmentStatus.READY,
    media_type: str = 'text/plain',
    session_id: str | None = _SESSION_ID,
    message_id: str | None = _MESSAGE_ID,
    generation: int = 1,
) -> MentorAttachment:
    attachment = MentorAttachment.create(
        _ATTACHMENT_ID,
        _ACCOUNT_ID,
        _BATCH_ID,
        'upload-key',
        'arquivo.txt' if media_type == 'text/plain' else 'arquivo.png',
        media_type,
        20,
        'a' * 64,
        f'mentor-attachments/{_ATTACHMENT_ID}/{generation}/original',
        _NOW,
    )
    attachment.status = status
    attachment.session_id = session_id
    attachment.message_id = message_id
    attachment.generation = generation
    attachment.preview_key = f'mentor-attachments/{_ATTACHMENT_ID}/1/preview'
    return attachment


def _chunk(
    *, attachment_id: str = _ATTACHMENT_ID, generation: int = 1
) -> MentorAttachmentChunk:
    return MentorAttachmentChunk(
        chunk_id='01JCHUNK0000000000000000001',
        attachment_id=attachment_id,
        generation=generation,
        page_number=1,
        locator='page:1',
        content='conteúdo da página',
    )


@pytest.fixture
def harness() -> dict[str, Any]:
    database = create_autospec(IntelligenceDatabase, instance=True)
    repositories = create_autospec(IntelligenceDatabaseRepositories, instance=True)
    repositories.mentor_attachment_batches = create_autospec(
        MentorAttachmentBatchesRepository, instance=True
    )
    repositories.mentor_attachments = create_autospec(
        MentorAttachmentsRepository, instance=True
    )
    repositories.mentor_attachment_chunks = create_autospec(
        MentorAttachmentChunksRepository, instance=True
    )
    repositories.mentor_sessions = create_autospec(
        MentorSessionsRepository, instance=True
    )
    repositories.mentor_attachments.find_by_batch_id.return_value = ()
    database.transaction.return_value.__enter__.return_value = repositories
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = _NOW
    identifier = create_autospec(IdentifierProvider, instance=True)
    identifier.generate.return_value = _BATCH_ID
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='revision-1',
        operation_key=_BATCH_ID,
    )
    storage = create_autospec(FileStorageProvider, instance=True)
    storage.read.return_value = b'private file bytes'
    return {
        'database': database,
        'repositories': repositories,
        'clock': clock,
        'identifier': identifier,
        'access': access,
        'storage': storage,
    }


def test_create_batch_scopes_access_and_schedules_cleanup(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()
    subject = CreateMentorAttachmentBatchUseCase(
        dependencies['database'],
        dependencies['identifier'],
        dependencies['clock'],
        dependencies['access'],
    )

    result = subject.execute(_ACCOUNT_ID, _SESSION_ID)

    assert result.batch_id == _BATCH_ID
    assert result.expires_at == _NOW + timedelta(hours=1)
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.assert_called_once_with(
        _ACCOUNT_ID, _SESSION_ID
    )
    batch = dependencies['repositories'].mentor_attachment_batches.add.call_args.args[0]
    assert batch.account_id == _ACCOUNT_ID
    assert batch.session_id == _SESSION_ID
    cleanup = dependencies['repositories'].events.add.call_args.args[0]
    assert cleanup.payload.batch_id == _BATCH_ID
    assert cleanup.payload.deletion_generation == 1
    assert dependencies['repositories'].events.add.call_args.kwargs == {
        'available_at': _NOW + timedelta(hours=1)
    }
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


def test_create_batch_rejects_missing_session_without_writes(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = None
    subject = CreateMentorAttachmentBatchUseCase(
        dependencies['database'],
        dependencies['identifier'],
        dependencies['clock'],
        dependencies['access'],
    )

    with pytest.raises(MentorSessionNotFoundError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID)

    dependencies['repositories'].mentor_attachment_batches.add.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()


@pytest.mark.parametrize(
    ('batch_id', 'session_id'),
    [('', None), (_BATCH_ID, '  ')],
)
def test_should_reject_invalid_batch_identity_or_session_before_writes(
    harness: dict[str, Any], batch_id: str, session_id: str | None
) -> None:
    dependencies = harness
    dependencies['identifier'].generate.return_value = batch_id
    subject = CreateMentorAttachmentBatchUseCase(
        dependencies['database'],
        dependencies['identifier'],
        dependencies['clock'],
        dependencies['access'],
    )

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(_ACCOUNT_ID, session_id)

    dependencies['database'].transaction.assert_not_called()
    dependencies['repositories'].mentor_attachment_batches.add.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()


def test_get_batch_renews_deadline_and_reads_attached_views(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    batch = _batch(session_id=_SESSION_ID)
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()
    attachment = _attachment()
    dependencies['repositories'].mentor_attachments.find_by_batch_id.return_value = (
        attachment,
    )
    subject = GetMentorAttachmentBatchUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    result = subject.execute(_ACCOUNT_ID, _BATCH_ID)

    assert result.batch_id == _BATCH_ID
    assert result.expires_at == _NOW + timedelta(hours=1)
    assert result.attachments[0].attachment_id == _ATTACHMENT_ID
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.assert_called_once_with(
        _BATCH_ID, for_update=True
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.update.assert_called_once_with(batch)
    cleanup = dependencies['repositories'].events.add.call_args.args[0]
    assert cleanup.payload.batch_id == _BATCH_ID
    assert dependencies['repositories'].events.add.call_args.kwargs == {
        'available_at': batch.expires_at
    }
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


def test_should_reject_batch_when_its_bound_session_is_missing(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = _batch(session_id=_SESSION_ID)
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = None
    subject = GetMentorAttachmentBatchUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    with pytest.raises(MentorSessionNotFoundError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID)

    dependencies['repositories'].mentor_attachment_batches.update.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()
    dependencies['repositories'].mentor_attachments.find_by_batch_id.assert_not_called()


@pytest.mark.parametrize('state', ['missing', 'foreign', 'revoked'])
def test_get_batch_hides_missing_foreign_and_revoked_batches(
    harness: dict[str, Any], state: str
) -> None:
    dependencies = harness
    batch = _batch()
    if state == 'missing':
        batch = None
    elif state == 'foreign':
        batch.account_id = _OTHER_ACCOUNT_ID
    else:
        batch.revoke(_NOW)
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    subject = GetMentorAttachmentBatchUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID)

    dependencies['repositories'].mentor_attachment_batches.update.assert_not_called()


def test_get_batch_rejects_expired_unconsumed_batch(harness: dict[str, Any]) -> None:
    dependencies = harness
    batch = _batch()
    batch.expires_at = _NOW
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    subject = GetMentorAttachmentBatchUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID)


def test_get_context_returns_only_current_authorized_chunks(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    attachment = _attachment()
    current = _chunk()
    stale = _chunk(generation=2)
    dependencies['repositories'].mentor_sessions.find_by_id.return_value = object()
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = attachment
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.find_many_eligible.return_value = (
        current,
        stale,
    )
    subject = GetMentorAttachmentContextUseCase(
        dependencies['database'], dependencies['identifier'], dependencies['access']
    )

    result = subject.execute(
        _ACCOUNT_ID, _SESSION_ID, (_ATTACHMENT_ID,), page_numbers=(1,)
    )

    assert result.chunks == (current,)
    assert result.sources[0].attachment_id == _ATTACHMENT_ID
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.find_many_eligible.assert_called_once_with(
        _ACCOUNT_ID, _SESSION_ID, (_ATTACHMENT_ID,), (1,)
    )
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


@pytest.mark.parametrize(
    'attachment_ids,page_numbers',
    [
        ((), ()),
        ((_ATTACHMENT_ID,) * 6, ()),
        ((_ATTACHMENT_ID, _ATTACHMENT_ID), ()),
        ((_ATTACHMENT_ID,), (0,)),
        ((_ATTACHMENT_ID,), (1, 1)),
    ],
)
def test_get_context_rejects_invalid_selection_before_authorization(
    harness: dict[str, Any],
    attachment_ids: tuple[str, ...],
    page_numbers: tuple[int, ...],
) -> None:
    dependencies = harness
    subject = GetMentorAttachmentContextUseCase(
        dependencies['database'], dependencies['identifier'], dependencies['access']
    )

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID, attachment_ids, page_numbers)

    dependencies['access'].authorize.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.find_many_eligible.assert_not_called()


def test_get_context_rejects_missing_session_or_unavailable_attachment(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    subject = GetMentorAttachmentContextUseCase(
        dependencies['database'], dependencies['identifier'], dependencies['access']
    )
    dependencies['repositories'].mentor_sessions.find_by_id.return_value = None
    with pytest.raises(MentorSessionNotFoundError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID, (_ATTACHMENT_ID,))

    dependencies['repositories'].mentor_sessions.find_by_id.return_value = object()
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = None
    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID, (_ATTACHMENT_ID,))

    dependencies[
        'repositories'
    ].mentor_attachment_chunks.find_many_eligible.assert_not_called()


def test_read_file_uses_private_preview_and_rechecks_current_generation(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    attachment = _attachment(media_type='image/png')
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = [
        attachment,
        attachment,
    ]
    subject = ReadMentorAttachmentFileUseCase(
        dependencies['database'],
        dependencies['identifier'],
        dependencies['access'],
        dependencies['storage'],
    )

    result = subject.execute(_ACCOUNT_ID, _SESSION_ID, _ATTACHMENT_ID, preview=True)

    assert result.content == b'private file bytes'
    assert result.filename == attachment.filename
    dependencies['storage'].read.assert_called_once_with(attachment.preview_key)
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [call(_ATTACHMENT_ID), call(_ATTACHMENT_ID, for_update=True)]
    )
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


def test_read_file_rejects_non_image_preview_before_authorization(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()
    dependencies[
        'repositories'
    ].mentor_attachments.find_by_id.return_value = _attachment()
    subject = ReadMentorAttachmentFileUseCase(
        dependencies['database'],
        dependencies['identifier'],
        dependencies['access'],
        dependencies['storage'],
    )

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID, _ATTACHMENT_ID, preview=True)

    dependencies['access'].authorize.assert_not_called()
    dependencies['storage'].read.assert_not_called()


def test_read_file_wraps_storage_failure_and_rejects_revoked_generation(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    attachment = _attachment()
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = attachment
    subject = ReadMentorAttachmentFileUseCase(
        dependencies['database'],
        dependencies['identifier'],
        dependencies['access'],
        dependencies['storage'],
    )
    dependencies['storage'].read.side_effect = OSError
    with pytest.raises(MentorAttachmentUnavailableError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID, _ATTACHMENT_ID, preview=False)

    dependencies['storage'].read.side_effect = None
    dependencies['storage'].read.return_value = b'private file bytes'
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = [
        attachment,
        _attachment(generation=2),
    ]
    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _SESSION_ID, _ATTACHMENT_ID, preview=False)


def test_remove_attachment_revokes_and_queues_private_cleanup(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    batch = _batch()
    attachment = _attachment()
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = attachment
    subject = RemoveMentorAttachmentUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)

    assert attachment.status is MentorAttachmentStatus.REMOVED
    assert attachment.generation == 2
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    cleanup = dependencies['repositories'].events.add.call_args.args[0]
    assert cleanup.payload.batch_id == _BATCH_ID
    assert cleanup.payload.deletion_generation == 2
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


def test_remove_attachment_is_idempotent_and_rejects_foreign_batch(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    batch = _batch()
    attachment = _attachment(status=MentorAttachmentStatus.REMOVED)
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = attachment
    subject = RemoveMentorAttachmentUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )
    subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()

    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = None
    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)


@pytest.mark.parametrize('batch_state', ['foreign', 'revoked', 'expired', 'consumed'])
def test_remove_attachment_rejects_unavailable_batch_without_writes(
    harness: dict[str, Any], batch_state: str
) -> None:
    dependencies = harness
    batch = _batch()
    if batch_state == 'foreign':
        batch.account_id = _OTHER_ACCOUNT_ID
    elif batch_state == 'revoked':
        batch.revoke(_NOW)
    elif batch_state == 'expired':
        batch.expires_at = _NOW
    else:
        batch.consumed_by_message_id = _MESSAGE_ID
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    dependencies[
        'repositories'
    ].mentor_attachments.find_by_id.return_value = _attachment()
    subject = RemoveMentorAttachmentUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()


@pytest.mark.parametrize('attachment_state', ['missing', 'foreign', 'wrong_batch'])
def test_remove_attachment_rejects_unavailable_attachment_without_writes(
    harness: dict[str, Any], attachment_state: str
) -> None:
    dependencies = harness
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = _batch()
    attachment = None if attachment_state == 'missing' else _attachment()
    if attachment is not None and attachment_state == 'foreign':
        attachment.account_id = _OTHER_ACCOUNT_ID
    elif attachment is not None and attachment_state == 'wrong_batch':
        attachment.batch_id = '01JBATCH00000000000000000002'
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = attachment
    subject = RemoveMentorAttachmentUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()


def test_remove_attachment_rechecks_access_after_scheduling_cleanup(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    batch = _batch()
    attachment = _attachment()
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = batch
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = attachment
    dependencies['access'].assert_current.side_effect = [None, RuntimeError('revoked')]
    subject = RemoveMentorAttachmentUseCase(
        dependencies['database'], dependencies['clock'], dependencies['access']
    )

    with pytest.raises(RuntimeError, match='revoked'):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)

    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies['repositories'].events.add.assert_called_once()
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])


def test_revoke_session_attachments_fences_attachments_and_batches(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    attachment = _attachment()
    batch = _batch(session_id=_SESSION_ID)
    dependencies['repositories'].mentor_attachments.find_by_session_id.return_value = (
        attachment,
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_session_id.return_value = (batch,)

    revoke_session_attachments(
        dependencies['repositories'],
        dependencies['access'],
        _ACCOUNT_ID,
        _SESSION_ID,
        _NOW,
    )

    assert attachment.status is MentorAttachmentStatus.REMOVED
    assert batch.revoked_at == _NOW
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.update.assert_called_once_with(batch)
    dependencies['repositories'].events.add.assert_called_once()


def test_revoke_session_attachments_schedules_fallback_cleanup_once(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_session_id.return_value = (
        _attachment(),
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_session_id.return_value = ()

    revoke_session_attachments(
        dependencies['repositories'],
        dependencies['access'],
        _ACCOUNT_ID,
        _SESSION_ID,
        _NOW,
    )

    dependencies['repositories'].events.add.assert_called_once()
    cleanup = dependencies['repositories'].events.add.call_args.args[0]
    assert cleanup.payload.session_id == _SESSION_ID
    assert cleanup.payload.deletion_generation == 2


def test_revoke_session_attachments_skips_removed_rows_and_does_not_duplicate_cleanup(
    harness: dict[str, Any],
) -> None:
    dependencies = harness
    attachment = _attachment(status=MentorAttachmentStatus.REMOVED)
    batch = _batch(session_id=_SESSION_ID)
    batch.revoke(_NOW)
    dependencies['repositories'].mentor_attachments.find_by_session_id.return_value = (
        attachment,
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_session_id.return_value = (batch,)

    revoke_session_attachments(
        dependencies['repositories'],
        dependencies['access'],
        _ACCOUNT_ID,
        _SESSION_ID,
        _NOW,
    )

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_batches.update.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()


def test_revoke_session_attachments_with_no_rows_has_no_cleanup_event(
    harness: dict[str, Any],
) -> None:
    dependencies = harness

    revoke_session_attachments(
        dependencies['repositories'],
        dependencies['access'],
        _ACCOUNT_ID,
        _SESSION_ID,
        _NOW,
    )

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies['repositories'].mentor_attachment_batches.update.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()

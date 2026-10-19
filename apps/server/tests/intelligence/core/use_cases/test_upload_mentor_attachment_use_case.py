from collections.abc import Iterator
from itertools import chain, cycle
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import call, create_autospec

import pytest
from sqlalchemy.exc import OperationalError
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentInvalidError,
    MentorAttachmentNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    MentorAttachmentCleanupRequestedEvent,
    MentorAttachmentPreparationRequestedEvent,
)
from shifu.intelligence.core.domain.structures import MentorAttachmentFile
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentExtractorProvider,
    MentorAttachmentsRepository,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import UploadMentorAttachmentUseCase
from shifu.shared.core.domain.errors import AuthorizationError, ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    EventsRepository,
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)

from tests.intelligence.core.use_cases.mentor_attachment_lock_order_setup import (
    LockRecorder,
)

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_UPLOAD_KEY = '123e4567-e89b-42d3-a456-426614174000'
_Harness = tuple[UploadMentorAttachmentUseCase, dict[str, Any]]


@pytest.fixture
def harness() -> _Harness:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch_created_at = now - timedelta(minutes=5)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID,
        _ACCOUNT_ID,
        None,
        batch_created_at,
        batch_created_at + timedelta(hours=1),
    )
    database = create_autospec(IntelligenceDatabase, instance=True)
    repositories = create_autospec(IntelligenceDatabaseRepositories, instance=True)
    repositories.mentor_attachment_batches = create_autospec(
        MentorAttachmentBatchesRepository, instance=True
    )
    repositories.mentor_attachments = create_autospec(
        MentorAttachmentsRepository, instance=True
    )
    repositories.events = create_autospec(EventsRepository, instance=True)
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.mentor_attachment_batches.find_by_id.return_value = batch
    repositories.mentor_attachments.find_by_upload_key.return_value = None
    repositories.mentor_attachments.count_active_in_batch.return_value = 0
    attachments: dict[str, MentorAttachment] = {}
    by_upload_key: dict[str, MentorAttachment] = {}

    def add(attachment: MentorAttachment) -> None:
        attachments[attachment.id] = attachment
        by_upload_key[attachment.upload_key] = attachment

    def find_by_id(
        attachment_id: str, *, for_update: bool = False
    ) -> MentorAttachment | None:
        del for_update
        return attachments.get(attachment_id)

    def find_by_upload_key(batch_id: str, upload_key: str) -> MentorAttachment | None:
        del batch_id
        return by_upload_key.get(upload_key)

    repositories.mentor_attachments.add.side_effect = add
    repositories.mentor_attachments.find_by_id.side_effect = find_by_id
    repositories.mentor_attachments.find_by_upload_key.side_effect = find_by_upload_key

    identifiers = create_autospec(IdentifierProvider, instance=True)
    identifiers.generate.return_value = '01JATTACHMENT00000000000001'
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='rev-1',
        operation_key=_UPLOAD_KEY,
    )
    storage = create_autospec(FileStorageProvider, instance=True)
    extractor = create_autospec(MentorAttachmentExtractorProvider, instance=True)
    subject = UploadMentorAttachmentUseCase(
        database, identifiers, clock, access, storage, extractor
    )
    return subject, {
        'batch': batch,
        'repositories': repositories,
        'clock': clock,
        'access': access,
        'storage': storage,
        'extractor': extractor,
        'attachments': attachments,
        'by_upload_key': by_upload_key,
    }


def _file(
    filename: str = 'notes.txt',
    media_type: str = 'text/plain',
    content: bytes = b'conteudo educacional',
) -> MentorAttachmentFile:
    return MentorAttachmentFile(
        filename=filename, media_type=media_type, content=content
    )


def test_upload_reserves_private_bytes_and_queues_preparation(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    result = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert result.created is True
    assert result.attachment.status is MentorAttachmentStatus.UPLOADING
    attachment = next(iter(dependencies['attachments'].values()))
    assert attachment.created_at == dependencies['clock'].now.return_value
    assert attachment.upload_completed_at == dependencies['clock'].now.return_value
    dependencies['access'].authorize.assert_called_once_with(_ACCOUNT_ID, _UPLOAD_KEY)
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls(
        [call(grant), call(grant), call(grant)]
    )
    dependencies['extractor'].validate.assert_called_once_with(
        b'conteudo educacional', 'text/plain'
    )
    dependencies['repositories'].mentor_attachment_batches.find_by_id.assert_has_calls(
        [
            call(_BATCH_ID, for_update=True),
            call(_BATCH_ID),
            call(_BATCH_ID, for_update=True),
        ]
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.update.assert_called_once_with(dependencies['batch'])
    dependencies['repositories'].mentor_attachments.find_by_id.assert_called_once_with(
        attachment.id, for_update=True
    )
    dependencies['storage'].put.assert_called_once_with(
        'mentor-attachments/01JATTACHMENT00000000000001/1/original',
        b'conteudo educacional',
        'text/plain',
    )
    event_calls = dependencies['repositories'].events.add.call_args_list
    assert isinstance(
        event_calls[-1].args[0], MentorAttachmentPreparationRequestedEvent
    )
    cleanup = event_calls[0].args[0]
    assert isinstance(cleanup, MentorAttachmentCleanupRequestedEvent)
    assert cleanup.payload.deletion_generation == dependencies['batch'].generation
    assert cleanup.payload.account_id == _ACCOUNT_ID
    assert cleanup.payload.batch_id == _BATCH_ID
    assert event_calls[0].kwargs['available_at'] == dependencies['batch'].expires_at
    preparation = event_calls[-1].args[0]
    assert preparation.payload.attachment_id == attachment.id
    assert preparation.payload.generation == attachment.generation


def test_exact_upload_key_replay_does_not_write_or_enqueue_again(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    first = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    replay = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert first.created is True
    assert replay.created is False
    assert replay.attachment.attachment_id == first.attachment.attachment_id
    dependencies['storage'].put.assert_called_once()
    assert dependencies['repositories'].events.add.call_count == 2
    dependencies[
        'repositories'
    ].mentor_attachments.find_by_upload_key.assert_called_with(_BATCH_ID, _UPLOAD_KEY)


def test_retry_finishes_upload_after_completion_transaction_failure(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    def fail_first_preparation_event(
        event: object, *, available_at: datetime | None = None
    ) -> None:
        del available_at
        if isinstance(event, MentorAttachmentPreparationRequestedEvent):
            attachment = next(iter(dependencies['attachments'].values()))
            # The mock transaction cannot roll back the entity mutation for us.
            attachment.upload_completed_at = None
            raise ServiceUnavailableError

    dependencies['repositories'].events.add.side_effect = fail_first_preparation_event
    with pytest.raises(ServiceUnavailableError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    attachment = next(iter(dependencies['attachments'].values()))
    assert attachment.status is MentorAttachmentStatus.UPLOADING
    assert attachment.upload_completed_at is None
    dependencies['repositories'].events.add.side_effect = None

    replay = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert replay.created is False
    assert replay.attachment.attachment_id == attachment.id
    assert attachment.upload_completed_at == dependencies['clock'].now.return_value
    assert dependencies['storage'].put.call_count == 2
    dependencies['storage'].remove.assert_not_called()
    preparation_events = [
        call.args[0]
        for call in dependencies['repositories'].events.add.call_args_list
        if isinstance(call.args[0], MentorAttachmentPreparationRequestedEvent)
    ]
    assert len(preparation_events) == 2


def test_retry_finishes_upload_after_raw_database_error(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    def fail_first_preparation_event(
        event: object, *, available_at: datetime | None = None
    ) -> None:
        del available_at
        if isinstance(event, MentorAttachmentPreparationRequestedEvent):
            attachment = next(iter(dependencies['attachments'].values()))
            # The mock transaction cannot roll back the entity mutation for us.
            attachment.upload_completed_at = None
            raise OperationalError('insert event', {}, RuntimeError('database down'))

    dependencies['repositories'].events.add.side_effect = fail_first_preparation_event
    with pytest.raises(OperationalError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    attachment = next(iter(dependencies['attachments'].values()))
    assert attachment.status is MentorAttachmentStatus.UPLOADING
    assert attachment.upload_completed_at is None
    dependencies['repositories'].events.add.side_effect = None

    replay = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert replay.created is False
    assert replay.attachment.attachment_id == attachment.id
    assert attachment.upload_completed_at == dependencies['clock'].now.return_value
    assert dependencies['storage'].put.call_count == 2
    dependencies['storage'].remove.assert_not_called()


def test_upload_key_reuse_with_different_bytes_conflicts(harness: _Harness) -> None:
    subject, _dependencies = harness
    subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(
            _ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file(content=b'different')
        )


def test_invalid_declared_media_type_fails_before_authorization(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(
            _ACCOUNT_ID,
            _BATCH_ID,
            _UPLOAD_KEY,
            _file(filename='notes.txt', media_type='application/pdf'),
        )

    dependencies['storage'].put.assert_not_called()
    dependencies['extractor'].validate.assert_not_called()


def test_storage_failure_preserves_failed_row_and_queues_cleanup(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['storage'].put.side_effect = ServiceUnavailableError()

    result = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert result.attachment.status is MentorAttachmentStatus.FAILED
    assert result.attachment.failure_code == 'storage_write_failed'
    assert result.created is True
    attachment = next(iter(dependencies['attachments'].values()))
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies['repositories'].mentor_attachments.find_by_id.assert_called_once_with(
        attachment.id, for_update=True
    )
    events = [
        call.args[0] for call in dependencies['repositories'].events.add.call_args_list
    ]
    assert isinstance(events[0], MentorAttachmentCleanupRequestedEvent)
    assert isinstance(events[-1], MentorAttachmentCleanupRequestedEvent)
    assert not any(
        isinstance(event, MentorAttachmentPreparationRequestedEvent) for event in events
    )
    assert events[-1].payload.account_id == _ACCOUNT_ID
    assert events[-1].payload.batch_id == _BATCH_ID
    assert events[-1].payload.deletion_generation == attachment.generation


def test_upload_respects_five_active_attachment_limit(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies[
        'repositories'
    ].mentor_attachments.count_active_in_batch.return_value = 5

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    dependencies['storage'].put.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachments.count_active_in_batch.assert_called_once_with(_BATCH_ID)


@pytest.mark.parametrize(
    'upload_key',
    ['not-a-uuid', '123e4567-e89b-12d3-a456-426614174000'],
)
def test_invalid_upload_key_fails_before_validation_or_access(
    harness: _Harness, upload_key: str
) -> None:
    subject, dependencies = harness

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, upload_key, _file())

    dependencies['extractor'].validate.assert_not_called()
    dependencies['storage'].put.assert_not_called()


@pytest.mark.parametrize(
    'uploaded_file',
    [
        _file(content=b''),
        _file(content=b'x' * 2_000_001),
        _file(filename=''),
        _file(filename='n' * 256 + '.txt'),
        _file(filename='n' * 252 + '.txt'),
        _file(filename='unsafe\nname.txt'),
        _file(filename='notes'),
        _file(filename='notes.bin', media_type='application/octet-stream'),
        _file(content=cast('bytes', bytearray(b'content'))),
    ],
    ids=[
        'empty-content',
        'oversized-content',
        'empty-filename',
        'long-filename',
        'filename-over-255-boundary',
        'control-character-filename',
        'missing-extension',
        'unsupported-media-type',
        'non-bytes-content',
    ],
)
def test_invalid_file_fails_before_access_or_storage(
    harness: _Harness, uploaded_file: MentorAttachmentFile
) -> None:
    subject, dependencies = harness

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, uploaded_file)

    dependencies['access'].authorize.assert_not_called()
    dependencies['extractor'].validate.assert_not_called()
    dependencies['storage'].put.assert_not_called()


@pytest.mark.parametrize(
    ('batch_state', 'error_type'),
    [
        ('missing', MentorAttachmentNotFoundError),
        ('foreign', MentorAttachmentNotFoundError),
        ('revoked', MentorAttachmentNotFoundError),
        ('expired', MentorAttachmentConflictError),
        ('consumed', MentorAttachmentConflictError),
    ],
)
def test_upload_rejects_missing_or_unavailable_batch_without_writes(
    harness: _Harness, batch_state: str, error_type: type[Exception]
) -> None:
    subject, dependencies = harness
    batch = dependencies['batch']
    if batch_state == 'foreign':
        batch.account_id = '01JOTHERACCOUNT00000000000001'
    elif batch_state == 'revoked':
        batch.revoke(dependencies['clock'].now.return_value)
    elif batch_state == 'expired':
        batch.expires_at = dependencies['clock'].now.return_value
    elif batch_state == 'consumed':
        batch.consumed_by_message_id = '01JMESSAGE000000000000000001'
    dependencies['repositories'].mentor_attachment_batches.find_by_id.return_value = (
        None if batch_state == 'missing' else batch
    )

    with pytest.raises(error_type):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    dependencies['repositories'].mentor_attachments.add.assert_not_called()
    dependencies['storage'].put.assert_not_called()
    assert not any(
        isinstance(event.args[0], MentorAttachmentPreparationRequestedEvent)
        for event in dependencies['repositories'].events.add.call_args_list
    )


@pytest.mark.parametrize('field', ['account_id', 'filename', 'media_type'])
def test_upload_key_replay_conflicts_when_reserved_metadata_diverges(
    harness: _Harness, field: str
) -> None:
    subject, dependencies = harness
    subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())
    attachment = next(iter(dependencies['attachments'].values()))
    replacement = {
        'account_id': '01JOTHERACCOUNT00000000000001',
        'filename': 'different.txt',
        'media_type': 'text/csv',
    }[field]
    setattr(attachment, field, replacement)

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert dependencies['storage'].put.call_count == 1
    assert dependencies['repositories'].events.add.call_count == 2


def test_upload_does_not_renew_a_batch_that_already_has_more_idle_time(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    batch = dependencies['batch']
    batch.expires_at = dependencies['clock'].now.return_value + timedelta(hours=2)

    subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert dependencies['repositories'].mentor_attachment_batches.update.call_count == 0
    event_calls = dependencies['repositories'].events.add.call_args_list
    assert len(event_calls) == 1
    assert isinstance(event_calls[0].args[0], MentorAttachmentPreparationRequestedEvent)


def test_upload_accepts_single_byte_and_normalizes_path_and_media_parameters(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    result = subject.execute(
        _ACCOUNT_ID,
        _BATCH_ID,
        _UPLOAD_KEY,
        _file(
            filename=r'C:\Learner\Notes.TXT',
            media_type='TEXT/PLAIN; charset=utf-8; boundary=learner-upload',
            content=b'x',
        ),
    )

    assert result.attachment.filename == 'Notes.TXT'
    assert result.attachment.size_bytes == 1
    dependencies['storage'].put.assert_called_once_with(
        'mentor-attachments/01JATTACHMENT00000000000001/1/original',
        b'x',
        'text/plain',
    )


def test_upload_accepts_maximum_content_and_filename_sizes(harness: _Harness) -> None:
    subject, _dependencies = harness
    filename = 'n' * 251 + '.txt'

    result = subject.execute(
        _ACCOUNT_ID,
        _BATCH_ID,
        _UPLOAD_KEY,
        _file(filename=filename, content=b'x' * 2_000_000),
    )

    assert result.attachment.filename == filename
    assert result.attachment.size_bytes == 2_000_000


@pytest.mark.parametrize('filename', ['archive.backup.txt', 'archive.backup.final.txt'])
def test_upload_resolves_extension_from_the_final_filename_suffix(
    harness: _Harness, filename: str
) -> None:
    subject, _dependencies = harness

    result = subject.execute(
        _ACCOUNT_ID,
        _BATCH_ID,
        _UPLOAD_KEY,
        _file(filename=filename, media_type='text/plain'),
    )

    assert result.attachment.filename == filename
    assert result.attachment.media_type == 'text/plain'


def test_upload_does_not_renew_when_deadline_already_matches_idle_window(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    batch = dependencies['batch']
    batch.expires_at = dependencies['clock'].now.return_value + timedelta(hours=1)

    subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    dependencies['repositories'].mentor_attachment_batches.update.assert_not_called()


@pytest.mark.parametrize(
    ('generation', 'status'),
    [
        (2, MentorAttachmentStatus.PROCESSING),
        (1, MentorAttachmentStatus.PROCESSING),
        (2, MentorAttachmentStatus.UPLOADING),
    ],
)
def test_storage_failure_does_not_overwrite_a_non_uploading_generation(
    harness: _Harness, generation: int, status: MentorAttachmentStatus
) -> None:
    subject, dependencies = harness

    def fail_after_new_generation(*_args: object, **_kwargs: object) -> None:
        attachment = next(iter(dependencies['attachments'].values()))
        attachment.generation = generation
        attachment.status = status
        raise ServiceUnavailableError

    dependencies['storage'].put.side_effect = fail_after_new_generation

    result = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert result.attachment.status is status
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    assert all(
        not isinstance(event.args[0], MentorAttachmentPreparationRequestedEvent)
        for event in dependencies['repositories'].events.add.call_args_list
    )


@pytest.mark.parametrize('completion_state', ['missing', 'new-generation', 'removed'])
def test_upload_rejects_stale_completion_and_removes_private_object(
    harness: _Harness, completion_state: str
) -> None:
    subject, dependencies = harness
    dependencies['storage'].remove.side_effect = ServiceUnavailableError

    def remove_reservation(*_args: object, **_kwargs: object) -> None:
        if completion_state == 'missing':
            dependencies['attachments'].clear()
            return
        attachment = next(iter(dependencies['attachments'].values()))
        attachment.generation = 2 if completion_state == 'new-generation' else 1
        attachment.status = (
            MentorAttachmentStatus.PROCESSING
            if completion_state == 'new-generation'
            else MentorAttachmentStatus.REMOVED
        )

    dependencies['storage'].put.side_effect = remove_reservation

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    dependencies['storage'].remove.assert_called_once_with(
        'mentor-attachments/01JATTACHMENT00000000000001/1/original'
    )
    assert all(
        not isinstance(event.args[0], MentorAttachmentPreparationRequestedEvent)
        for event in dependencies['repositories'].events.add.call_args_list
    )


@pytest.mark.parametrize(
    'batch_state',
    ['missing', 'foreign', 'revoked', 'expired', 'consumed', 'session', 'unbound'],
)
def test_upload_revokes_completion_when_batch_becomes_unavailable(
    harness: _Harness, batch_state: str
) -> None:
    subject, dependencies = harness
    batch = dependencies['batch']

    def invalidate_batch(*_args: object, **_kwargs: object) -> None:
        if batch_state == 'missing':
            dependencies[
                'repositories'
            ].mentor_attachment_batches.find_by_id.return_value = None
        elif batch_state == 'foreign':
            batch.account_id = '01JOTHERACCOUNT00000000000001'
        elif batch_state == 'revoked':
            batch.revoke(dependencies['clock'].now.return_value)
        elif batch_state == 'expired':
            batch.expires_at = dependencies['clock'].now.return_value
        elif batch_state == 'consumed':
            batch.consumed_by_message_id = '01JMESSAGE000000000000000001'
        elif batch_state == 'session':
            batch.session_id = '01JSESSION000000000000000001'
            dependencies[
                'repositories'
            ].mentor_sessions.find_by_id_for_update.return_value = None
        else:
            dependencies[
                'repositories'
            ].mentor_sessions.find_by_id_for_update.return_value = None

    dependencies['storage'].put.side_effect = invalidate_batch

    result = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    if batch_state == 'unbound':
        assert result.attachment.status is MentorAttachmentStatus.UPLOADING
        assert isinstance(
            dependencies['repositories'].events.add.call_args_list[-1].args[0],
            MentorAttachmentPreparationRequestedEvent,
        )
        dependencies[
            'repositories'
        ].mentor_sessions.find_by_id_for_update.assert_not_called()
        return

    assert result.attachment.status is MentorAttachmentStatus.REMOVED
    assert result.created is True
    attachment = next(iter(dependencies['attachments'].values()))
    assert attachment.generation == 2
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    event_calls = dependencies['repositories'].events.add.call_args_list
    assert isinstance(event_calls[-1].args[0], MentorAttachmentCleanupRequestedEvent)
    cleanup = event_calls[-1].args[0]
    assert cleanup.payload.account_id == _ACCOUNT_ID
    assert cleanup.payload.batch_id == _BATCH_ID
    assert cleanup.payload.deletion_generation == 2
    assert all(
        not isinstance(event.args[0], MentorAttachmentPreparationRequestedEvent)
        for event in event_calls
    )


def test_access_revocation_after_upload_fails_closed_and_cleans_object(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['access'].assert_current.side_effect = [
        None,
        None,
        AuthorizationError(),
    ]

    with pytest.raises(AuthorizationError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    dependencies['storage'].remove.assert_called_once_with(
        'mentor-attachments/01JATTACHMENT00000000000001/1/original'
    )
    attachment = next(iter(dependencies['attachments'].values()))
    assert attachment.status is MentorAttachmentStatus.REMOVED
    event_calls = dependencies['repositories'].events.add.call_args_list
    assert isinstance(event_calls[-1].args[0], MentorAttachmentCleanupRequestedEvent)
    cleanup = event_calls[-1].args[0]
    assert cleanup.payload.account_id == _ACCOUNT_ID
    assert cleanup.payload.batch_id == _BATCH_ID
    assert cleanup.payload.deletion_generation == attachment.generation


def test_upload_completes_bound_batch_when_session_is_still_owned(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    session_id = '01JSESSION000000000000000001'
    dependencies['batch'].session_id = session_id
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = object()

    result = subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert result.attachment.status is MentorAttachmentStatus.UPLOADING
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.assert_called_once_with(
        _ACCOUNT_ID, session_id
    )
    assert isinstance(
        dependencies['repositories'].events.add.call_args_list[-1].args[0],
        MentorAttachmentPreparationRequestedEvent,
    )


_SESSION_ID = '01JSESSION000000000000000001'


def _batch(session_id: str | None) -> MentorAttachmentBatch:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    return MentorAttachmentBatch.create(
        _BATCH_ID,
        _ACCOUNT_ID,
        session_id,
        now - timedelta(minutes=5),
        now + timedelta(hours=1),
    )


def _lock_recorder(
    dependencies: dict[str, Any], batches: Iterator[MentorAttachmentBatch | None]
) -> LockRecorder:
    repositories = dependencies['repositories']
    repositories.mentor_sessions = create_autospec(
        MentorSessionsRepository, instance=True
    )
    return LockRecorder(repositories, batches)


@pytest.mark.parametrize(
    ('session_id', 'expected'),
    [
        (_SESSION_ID, ['batch', 'session', 'batch', 'attachment']),
        (None, ['batch', 'batch', 'attachment']),
    ],
)
def test_should_lock_session_then_batch_then_attachment_when_completing_upload(
    harness: _Harness, session_id: str | None, expected: list[str]
) -> None:
    subject, dependencies = harness
    recorder = _lock_recorder(dependencies, cycle([_batch(session_id)]))

    subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert recorder.order == expected


def test_should_restart_upload_completion_with_session_lock_first_when_batch_gets_bound(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    unbound, bound = _batch(None), _batch(_SESSION_ID)
    recorder = _lock_recorder(
        dependencies, iter([unbound, unbound, bound, bound, bound])
    )

    subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert recorder.order == ['batch', 'batch', 'session', 'batch', 'attachment']


def test_should_raise_conflict_when_upload_batch_scope_keeps_changing(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    unbound, bound = _batch(None), _batch(_SESSION_ID)
    recorder = _lock_recorder(dependencies, chain([unbound], cycle([unbound, bound])))

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(_ACCOUNT_ID, _BATCH_ID, _UPLOAD_KEY, _file())

    assert recorder.order == ['batch', 'batch', 'batch', 'batch']
    dependencies['repositories'].events.add.assert_not_called()

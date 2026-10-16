import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorAttachmentNotFoundError,
    MentorAttachmentUnavailableError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentsRepository,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import PrepareMentorAttachmentUseCase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    FileStorageProvider,
    MentorAccessProvider,
)

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_SESSION_ID = '01JSESSION000000000000000001'
_EXECUTION_OWNER = 'preparation-worker'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)
_CONTENT = b'private source bytes'
_Harness = tuple[PrepareMentorAttachmentUseCase, dict[str, Any]]


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
        len(_CONTENT),
        hashlib.sha256(_CONTENT).hexdigest(),
        f'mentor-attachments/{_ATTACHMENT_ID}/1/original',
        _NOW,
    )
    database = create_autospec(IntelligenceDatabase, instance=True)
    repositories = create_autospec(IntelligenceDatabaseRepositories, instance=True)
    repositories.mentor_attachments = create_autospec(
        MentorAttachmentsRepository, instance=True
    )
    repositories.mentor_attachment_batches = create_autospec(
        MentorAttachmentBatchesRepository, instance=True
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
    grant = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='revision-1',
        operation_key=_ATTACHMENT_ID,
    )
    access.authorize.return_value = grant
    storage = create_autospec(FileStorageProvider, instance=True)
    storage.read.return_value = _CONTENT
    subject = PrepareMentorAttachmentUseCase(database, clock, access, storage)
    return subject, {
        'attachment': attachment,
        'batch': batch,
        'repositories': repositories,
        'access': access,
        'storage': storage,
    }


def test_prepare_claims_authorized_generation_and_returns_private_source(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    prepared = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert prepared is not None
    assert prepared.attachment_id == _ATTACHMENT_ID
    assert prepared.generation == 1
    assert prepared.execution_owner == _EXECUTION_OWNER
    assert prepared.media_type == 'text/plain'
    assert prepared.content == _CONTENT
    assert dependencies['attachment'].status is MentorAttachmentStatus.PROCESSING
    assert dependencies['attachment'].claim_expires_at == _NOW + timedelta(minutes=5)
    dependencies['access'].authorize.assert_called_once_with(
        _ACCOUNT_ID, _ATTACHMENT_ID
    )
    dependencies['storage'].read.assert_called_once_with(
        f'mentor-attachments/{_ATTACHMENT_ID}/1/original'
    )


def test_prepare_rehydrates_an_active_claim_owned_by_the_same_event(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    first = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)
    assert first is not None

    recovered = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert recovered is not None
    assert recovered.content == _CONTENT
    assert recovered.execution_owner == _EXECUTION_OWNER
    assert dependencies['storage'].read.call_count == 2
    assert dependencies['repositories'].mentor_attachments.update.call_count == 2


@pytest.mark.parametrize('generation,owner', [(2, _EXECUTION_OWNER), (1, 'other')])
def test_prepare_does_not_read_when_generation_or_live_claim_is_stale(
    harness: _Harness, generation: int, owner: str
) -> None:
    subject, dependencies = harness
    if owner == 'other':
        dependencies['attachment'].claim(
            'existing-worker', _NOW, _NOW + timedelta(minutes=2)
        )

    prepared = subject.execute(_ATTACHMENT_ID, generation, owner)

    assert prepared is None
    dependencies['storage'].read.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


@pytest.mark.parametrize('batch_state', ['foreign', 'revoked', 'expired', 'consumed'])
def test_prepare_does_not_claim_foreign_revoked_expired_or_consumed_batch(
    harness: _Harness, batch_state: str
) -> None:
    subject, dependencies = harness
    batch = dependencies['batch']
    if batch_state == 'foreign':
        batch.account_id = '01JOTHERACCOUNT00000000000001'
    elif batch_state == 'revoked':
        batch.revoke(_NOW)
    elif batch_state == 'expired':
        batch.expires_at = _NOW
    else:
        batch.consume('message-id')

    prepared = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert prepared is None
    assert dependencies['attachment'].status is MentorAttachmentStatus.UPLOADING
    dependencies['storage'].read.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_prepare_fences_a_missing_session_before_reading(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['batch'].session_id = _SESSION_ID
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = None

    with pytest.raises(MentorSessionNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    dependencies['storage'].read.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_prepare_does_not_claim_after_authorization_is_revoked(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['access'].assert_current.side_effect = PermissionError

    with pytest.raises(PermissionError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    dependencies['storage'].read.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_prepare_releases_claim_when_storage_bytes_do_not_match_checksum(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['storage'].read.return_value = b'changed private source'

    with pytest.raises(MentorAttachmentUnavailableError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    attachment = dependencies['attachment']
    assert attachment.status is MentorAttachmentStatus.PROCESSING
    assert attachment.execution_owner is None
    assert attachment.claim_expires_at is None
    assert dependencies['repositories'].mentor_attachments.update.call_count == 2


@pytest.mark.parametrize(('generation', 'owner'), [(0, _EXECUTION_OWNER), (1, '  ')])
def test_should_reject_invalid_claim_input_before_reading(
    harness: _Harness, generation: int, owner: str
) -> None:
    subject, dependencies = harness

    with pytest.raises(MentorAttachmentConflictError):
        subject.execute(_ATTACHMENT_ID, generation, owner)

    dependencies['repositories'].mentor_attachments.find_by_id.assert_not_called()
    dependencies['storage'].read.assert_not_called()


def test_should_reject_a_missing_attachment_before_authorization(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = None

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    dependencies['access'].authorize.assert_not_called()
    dependencies['storage'].read.assert_not_called()


def test_should_reject_an_attachment_that_disappears_before_claiming(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = (
        dependencies['attachment'],
        None,
    )

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    dependencies['storage'].read.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


@pytest.mark.parametrize(
    'status',
    [
        MentorAttachmentStatus.READY,
        MentorAttachmentStatus.FAILED,
        MentorAttachmentStatus.REMOVED,
    ],
)
def test_should_not_claim_an_attachment_that_is_not_uploading_or_processing(
    harness: _Harness, status: MentorAttachmentStatus
) -> None:
    subject, dependencies = harness
    dependencies['attachment'].status = status

    assert subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER) is None

    dependencies['storage'].read.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_should_release_claim_when_storage_read_fails(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['storage'].read.side_effect = OSError('private store unavailable')

    with pytest.raises(MentorAttachmentUnavailableError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    attachment = dependencies['attachment']
    assert attachment.execution_owner is None
    assert attachment.claim_expires_at is None
    assert dependencies['repositories'].mentor_attachments.update.call_count == 2


def test_should_discard_private_bytes_when_attachment_changes_after_read(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = (
        dependencies['attachment'],
        dependencies['attachment'],
        None,
    )

    assert subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER) is None

    dependencies['storage'].read.assert_called_once()
    assert dependencies['repositories'].mentor_attachments.update.call_count == 1


def test_should_discard_private_bytes_when_bound_session_disappears_after_read(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['batch'].session_id = _SESSION_ID
    dependencies['repositories'].mentor_sessions.find_by_id_for_update.side_effect = (
        object(),
        None,
    )

    assert subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER) is None

    dependencies['storage'].read.assert_called_once()
    dependencies['repositories'].mentor_attachments.update.assert_called_once()


def test_should_discard_private_bytes_when_batch_is_revoked_after_read(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    def revoke_batch(_object_key: str) -> bytes:
        dependencies['batch'].revoke(_NOW)
        return _CONTENT

    dependencies['storage'].read.side_effect = revoke_batch

    assert subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER) is None

    dependencies['storage'].read.assert_called_once()
    dependencies['repositories'].mentor_attachments.update.assert_called_once()


def test_should_preserve_a_replacement_claim_when_storage_read_fails(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    def replace_claim_then_fail(_object_key: str) -> bytes:
        dependencies['attachment'].execution_owner = 'replacement-worker'
        raise OSError('private store unavailable')

    dependencies['storage'].read.side_effect = replace_claim_then_fail

    with pytest.raises(MentorAttachmentUnavailableError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert dependencies['attachment'].execution_owner == 'replacement-worker'
    dependencies['repositories'].mentor_attachments.update.assert_called_once()

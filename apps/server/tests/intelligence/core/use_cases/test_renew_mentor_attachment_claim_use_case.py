from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import call, create_autospec

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentsRepository,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import RenewMentorAttachmentClaimUseCase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_SESSION_ID = '01JSESSION000000000000000001'
_EXECUTION_OWNER = 'preparation-worker'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)
_Harness = tuple[RenewMentorAttachmentClaimUseCase, dict[str, Any]]


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
        10,
        'a' * 64,
        f'mentor-attachments/{_ATTACHMENT_ID}/1/original',
        _NOW,
    )
    attachment.claim(
        _EXECUTION_OWNER, _NOW - timedelta(minutes=1), _NOW + timedelta(minutes=1)
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
    access.authorize.return_value = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='revision-1',
        operation_key=_ATTACHMENT_ID,
    )
    subject = RenewMentorAttachmentClaimUseCase(database, clock, access)
    return subject, {
        'attachment': attachment,
        'batch': batch,
        'repositories': repositories,
        'access': access,
    }


def test_renew_extends_only_the_current_claim(harness: _Harness) -> None:
    subject, dependencies = harness
    grant = dependencies['access'].authorize.return_value

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is True
    assert dependencies['attachment'].execution_owner == _EXECUTION_OWNER
    assert dependencies['attachment'].claim_expires_at == _NOW + timedelta(minutes=5)
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        dependencies['attachment']
    )
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [
            call(_ATTACHMENT_ID),
            call(_ATTACHMENT_ID, for_update=True),
        ]
    )
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.assert_called_once_with(
        _BATCH_ID, for_update=True
    )
    dependencies['access'].authorize.assert_called_once_with(
        _ACCOUNT_ID, _ATTACHMENT_ID
    )
    assert dependencies['access'].assert_current.call_args_list == [
        call(grant),
        call(grant),
    ]


def test_renew_rejects_a_missing_attachment_without_authorizing(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = None

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is False
    dependencies['repositories'].mentor_attachments.find_by_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['access'].authorize.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_renew_rejects_an_attachment_deleted_before_it_is_locked(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = [
        dependencies['attachment'],
        None,
    ]

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is False
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [
            call(_ATTACHMENT_ID),
            call(_ATTACHMENT_ID, for_update=True),
        ]
    )
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_renew_rejects_a_missing_batch(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = None

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is False
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.assert_called_once_with(
        _BATCH_ID, for_update=True
    )
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_renew_checks_a_bound_session_under_lock(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['batch'].session_id = _SESSION_ID
    session = object()
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = session

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is True
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.assert_called_once_with(
        _ACCOUNT_ID, _SESSION_ID
    )
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        dependencies['attachment']
    )


@pytest.mark.parametrize(
    'generation,owner,expired',
    [
        (2, _EXECUTION_OWNER, False),
        (1, 'stale-worker', False),
        (1, _EXECUTION_OWNER, True),
    ],
)
def test_renew_rejects_stale_generation_owner_or_expired_lease(
    harness: _Harness, generation: int, owner: str, expired: bool
) -> None:
    subject, dependencies = harness
    if expired:
        dependencies['attachment'].claim_expires_at = _NOW

    renewed = subject.execute(_ATTACHMENT_ID, generation, owner)

    assert renewed is False
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


@pytest.mark.parametrize('batch_state', ['revoked', 'expired', 'consumed'])
def test_renew_rejects_a_batch_that_is_not_active(
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

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is False
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_renew_rejects_a_missing_session(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['batch'].session_id = _SESSION_ID
    dependencies[
        'repositories'
    ].mentor_sessions.find_by_id_for_update.return_value = None

    renewed = subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert renewed is False
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_renew_does_not_write_after_authorization_is_revoked(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['access'].assert_current.side_effect = PermissionError

    with pytest.raises(PermissionError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    dependencies['repositories'].mentor_attachments.update.assert_not_called()

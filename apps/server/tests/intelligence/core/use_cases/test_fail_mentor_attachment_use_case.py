from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import call, create_autospec

import pytest
from shifu.intelligence.core.domain.entities import MentorAttachment
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import MentorAttachmentNotFoundError
from shifu.intelligence.core.domain.events import MentorAttachmentCleanupRequestedEvent
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentChunksRepository,
    MentorAttachmentsRepository,
)
from shifu.intelligence.core.use_cases import FailMentorAttachmentUseCase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    EventsRepository,
    MentorAccessProvider,
)

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_EXECUTION_OWNER = 'preparation-worker'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)
_Harness = tuple[FailMentorAttachmentUseCase, dict[str, Any]]


@pytest.fixture
def harness() -> _Harness:
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
        _EXECUTION_OWNER, _NOW - timedelta(minutes=1), _NOW + timedelta(minutes=4)
    )
    database = create_autospec(IntelligenceDatabase, instance=True)
    repositories = create_autospec(IntelligenceDatabaseRepositories, instance=True)
    repositories.mentor_attachments = create_autospec(
        MentorAttachmentsRepository, instance=True
    )
    repositories.mentor_attachment_chunks = create_autospec(
        MentorAttachmentChunksRepository, instance=True
    )
    repositories.events = create_autospec(EventsRepository, instance=True)
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.mentor_attachments.find_by_id.return_value = attachment
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = _NOW
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='revision-1',
        operation_key=_ATTACHMENT_ID,
    )
    subject = FailMentorAttachmentUseCase(database, clock, access)
    return subject, {
        'attachment': attachment,
        'repositories': repositories,
        'access': access,
    }


@pytest.mark.parametrize(
    'failure_code',
    [
        'invalid_file',
        'unreadable_file',
        'analysis_unavailable',
        'attachment_unavailable',
    ],
)
def test_fail_queues_private_object_cleanup_for_every_terminal_failure(
    harness: _Harness, failure_code: str
) -> None:
    subject, dependencies = harness

    subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, failure_code)

    event = dependencies['repositories'].events.add.call_args.args[0]
    assert isinstance(event, MentorAttachmentCleanupRequestedEvent)
    assert event.payload.account_id == _ACCOUNT_ID
    assert event.payload.session_id is None
    assert event.payload.batch_id == _BATCH_ID
    assert event.payload.deletion_generation == dependencies['attachment'].generation
    dependencies['repositories'].events.add.assert_called_once()


def test_fail_records_safe_failure_and_removes_old_chunks(harness: _Harness) -> None:
    subject, dependencies = harness

    status = subject.execute(
        _ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'analysis_unavailable'
    )

    attachment = dependencies['attachment']
    assert status is MentorAttachmentStatus.FAILED
    assert attachment.failure_code == 'analysis_unavailable'
    assert attachment.execution_owner is None
    assert attachment.claim_expires_at is None
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies['access'].authorize.assert_called_once_with(
        _ACCOUNT_ID, _ATTACHMENT_ID
    )
    grant = dependencies['access'].authorize.return_value
    dependencies['access'].assert_current.assert_has_calls([call(grant), call(grant)])
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [call(_ATTACHMENT_ID), call(_ATTACHMENT_ID, for_update=True)]
    )


@pytest.mark.parametrize(
    'generation,owner', [(2, _EXECUTION_OWNER), (1, 'stale-worker')]
)
def test_fail_ignores_stale_generation_or_execution_owner(
    harness: _Harness, generation: int, owner: str
) -> None:
    subject, dependencies = harness

    status = subject.execute(
        _ATTACHMENT_ID, generation, owner, 'attachment_unavailable'
    )

    assert status is MentorAttachmentStatus.PROCESSING
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_not_called()
    dependencies['repositories'].events.add.assert_not_called()


def test_fail_ignores_expired_claim(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['attachment'].claim_expires_at = _NOW

    status = subject.execute(
        _ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable'
    )

    assert status is MentorAttachmentStatus.PROCESSING
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_fail_ignores_attachment_without_claim_expiry(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['attachment'].claim_expires_at = None

    status = subject.execute(
        _ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable'
    )

    assert status is MentorAttachmentStatus.PROCESSING
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_not_called()


def test_fail_ignores_attachment_that_is_not_processing(harness: _Harness) -> None:
    subject, dependencies = harness
    attachment = dependencies['attachment']
    attachment.status = MentorAttachmentStatus.READY
    attachment.execution_owner = _EXECUTION_OWNER
    attachment.claim_expires_at = _NOW + timedelta(minutes=1)

    status = subject.execute(
        _ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable'
    )

    assert status is MentorAttachmentStatus.READY
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_not_called()


def test_fail_validates_failure_code_before_opening_a_transaction(
    harness: _Harness,
) -> None:
    subject, dependencies = harness

    with pytest.raises(ValueError) as error:
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'unsafe failure detail')

    assert str(error.value) == 'Unsupported mentor attachment failure code'
    dependencies['repositories'].mentor_attachments.find_by_id.assert_not_called()


def test_fail_does_not_mutate_after_authorization_is_revoked(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['access'].assert_current.side_effect = PermissionError

    with pytest.raises(PermissionError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable')

    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_not_called()


def test_fail_raises_for_missing_attachment(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = None

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable')

    dependencies['repositories'].mentor_attachments.find_by_id.assert_called_once_with(
        _ATTACHMENT_ID
    )
    dependencies['access'].authorize.assert_not_called()


def test_fail_raises_if_attachment_disappears_after_authorization(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = [
        dependencies['attachment'],
        None,
    ]

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable')

    dependencies['access'].assert_current.assert_called_once_with(
        dependencies['access'].authorize.return_value
    )
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [call(_ATTACHMENT_ID), call(_ATTACHMENT_ID, for_update=True)]
    )
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_fail_raises_if_attachment_changes_accounts_after_authorization(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    attachment = dependencies['attachment']
    other_account_attachment = MentorAttachment.create(
        _ATTACHMENT_ID,
        '01JACCOUNT000000000000000002',
        _BATCH_ID,
        'upload-key',
        'notes.txt',
        'text/plain',
        10,
        'a' * 64,
        f'mentor-attachments/{_ATTACHMENT_ID}/1/original',
        _NOW,
    )
    other_account_attachment.claim(
        _EXECUTION_OWNER, _NOW - timedelta(minutes=1), _NOW + timedelta(minutes=4)
    )
    dependencies['repositories'].mentor_attachments.find_by_id.side_effect = [
        attachment,
        other_account_attachment,
    ]

    with pytest.raises(MentorAttachmentNotFoundError):
        subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER, 'attachment_unavailable')

    dependencies['access'].assert_current.assert_called_once_with(
        dependencies['access'].authorize.return_value
    )
    dependencies['repositories'].mentor_attachments.find_by_id.assert_has_calls(
        [call(_ATTACHMENT_ID), call(_ATTACHMENT_ID, for_update=True)]
    )
    dependencies['repositories'].mentor_attachments.update.assert_not_called()

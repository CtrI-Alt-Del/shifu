from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentUnavailableError,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentChunksRepository,
    MentorAttachmentsRepository,
)
from shifu.intelligence.core.use_cases import PurgeMentorAttachmentsUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider, FileStorageProvider

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'


def _attachment(
    attachment_id: str, batch_id: str, now: datetime, status: MentorAttachmentStatus
) -> MentorAttachment:
    attachment = MentorAttachment.create(
        attachment_id=attachment_id,
        account_id=_ACCOUNT_ID,
        batch_id=batch_id,
        upload_key=f'upload-{attachment_id}',
        filename=f'{attachment_id}.txt',
        media_type='text/plain',
        size_bytes=1,
        checksum='a' * 64,
        object_key=f'mentor-attachments/{attachment_id}/1/original',
        now=now,
    )
    if status is MentorAttachmentStatus.REMOVED:
        attachment.revoke()
    else:
        attachment.status = status
    return attachment


def _harness(
    batch: MentorAttachmentBatch,
    attachments: tuple[MentorAttachment, ...],
    now: datetime,
) -> tuple[PurgeMentorAttachmentsUseCase, dict[str, Mock]]:
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
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.mentor_attachment_batches.find_by_id.return_value = batch
    repositories.mentor_attachments.find_by_batch_id.return_value = attachments
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    storage = create_autospec(FileStorageProvider, instance=True)
    subject = PurgeMentorAttachmentsUseCase(database, clock, storage)
    return subject, {
        'repositories': repositories,
        'storage': storage,
    }


def test_individual_cleanup_purges_only_removed_attachment_with_matching_generation() -> (
    None
):
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    removed = _attachment(
        '01JREMOVED000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.REMOVED
    )
    active_sibling = _attachment(
        '01JACTIVE0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    active_sibling.generation = removed.generation
    subject, dependencies = _harness(batch, (removed, active_sibling), now)

    removed_count = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, removed.generation)

    assert removed_count == 1
    dependencies['storage'].remove.assert_called_once_with(removed.object_key)
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        removed.id
    )
    assert active_sibling.status is MentorAttachmentStatus.READY


def test_should_purge_storage_failed_attachment_for_its_matching_generation() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    failed = _attachment(
        '01JFAILED0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.FAILED
    )
    failed.failure_code = 'storage_write_failed'
    subject, dependencies = _harness(batch, (failed,), now)

    removed_count = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, failed.generation)

    assert removed_count == 1
    assert failed.status is MentorAttachmentStatus.REMOVED
    dependencies['storage'].remove.assert_called_once_with(failed.object_key)
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        failed
    )


@pytest.mark.parametrize(
    'failure_code', ['invalid_file', 'unreadable_file', 'analysis_unavailable']
)
def test_should_purge_private_bytes_of_terminal_failure_but_keep_visible_failure(
    failure_code: str,
) -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    batch.consumed_by_message_id = 'message-1'
    failed = _attachment(
        '01JFAILED0000000000000000002', _BATCH_ID, now, MentorAttachmentStatus.FAILED
    )
    failed.failure_code = failure_code
    failed.preview_key = f'mentor-attachments/{failed.id}/1/preview'
    subject, dependencies = _harness(batch, (failed,), now)

    removed_count = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, failed.generation)

    assert removed_count == 2
    assert failed.status is MentorAttachmentStatus.FAILED
    assert failed.failure_code == failure_code
    dependencies['storage'].remove.assert_has_calls(
        [call(failed.object_key), call(failed.preview_key)]
    )
    dependencies['repositories'].mentor_attachments.update.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        failed.id
    )


def test_terminal_failure_purge_ignores_other_generations_and_siblings() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    batch.consumed_by_message_id = 'message-1'
    failed = _attachment(
        '01JFAILED0000000000000000003', _BATCH_ID, now, MentorAttachmentStatus.FAILED
    )
    failed.failure_code = 'unreadable_file'
    ready = _attachment(
        '01JREADY00000000000000000003', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    subject, dependencies = _harness(batch, (failed, ready), now)

    stale = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, failed.generation + 1)
    current = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, failed.generation)

    assert stale == 0
    assert current == 1
    dependencies['storage'].remove.assert_called_once_with(failed.object_key)
    assert ready.status is MentorAttachmentStatus.READY


def test_stale_expiry_generation_does_not_remove_current_batch_files() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now - timedelta(hours=2), now - timedelta(hours=1)
    )
    batch.generation = 2
    active = _attachment(
        '01JACTIVE0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    subject, dependencies = _harness(batch, (active,), now)

    removed_count = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, 1)

    assert removed_count == 0
    dependencies['storage'].remove.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_current_expiry_purges_unconsumed_batch_and_retains_rows_as_removed() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now - timedelta(hours=2), now - timedelta(hours=1)
    )
    attachment = _attachment(
        '01JACTIVE0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    attachment.preview_key = 'mentor-attachments/preview/1'
    subject, dependencies = _harness(batch, (attachment,), now)

    removed_count = subject.execute(_ACCOUNT_ID, None, _BATCH_ID, batch.generation)

    assert removed_count == 2
    assert attachment.status is MentorAttachmentStatus.REMOVED
    dependencies['storage'].remove.assert_has_calls(
        [call(attachment.object_key), call(attachment.preview_key)]
    )
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )
    dependencies[
        'repositories'
    ].mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        attachment.id
    )


def test_should_purge_files_chunks_attachments_and_batches_for_deleted_account() -> (
    None
):
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    attachment = _attachment(
        '01JACTIVE0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    attachment.preview_key = 'mentor-attachments/preview/1'
    subject, dependencies = _harness(batch, (attachment,), now)
    repositories = dependencies['repositories']
    repositories.mentor_attachment_batches.find_by_account_id.return_value = (batch,)
    repositories.mentor_attachments.find_for_cleanup.return_value = (attachment,)

    removed_count = subject.execute_for_deleted_account(_ACCOUNT_ID)

    assert removed_count == 2
    assert attachment.status is MentorAttachmentStatus.REMOVED
    dependencies['storage'].remove.assert_has_calls(
        [call(attachment.object_key), call(attachment.preview_key)]
    )
    repositories.mentor_attachment_chunks.remove_by_attachment_id.assert_called_once_with(
        attachment.id
    )
    repositories.mentor_attachments.remove.assert_called_once_with(attachment.id)
    repositories.mentor_attachment_batches.remove.assert_called_once_with(batch.id)


def test_should_purge_revoked_batches_for_a_session() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID,
        _ACCOUNT_ID,
        '01JSESSION000000000000000001',
        now,
        now + timedelta(hours=1),
    )
    batch.revoke(now)
    attachment = _attachment(
        '01JACTIVE0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    subject, dependencies = _harness(batch, (attachment,), now)
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_session_id.return_value = (batch,)

    removed_count = subject.execute(
        _ACCOUNT_ID, batch.session_id, None, batch.generation
    )

    assert removed_count == 1
    assert attachment.status is MentorAttachmentStatus.REMOVED
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_session_id.assert_called_once_with(
        _ACCOUNT_ID, batch.session_id
    )


@pytest.mark.parametrize(
    ('account_id', 'session_id', 'batch_id', 'generation'),
    [
        ('', None, _BATCH_ID, 1),
        (_ACCOUNT_ID, None, None, 1),
        (_ACCOUNT_ID, 'session', _BATCH_ID, 1),
        (_ACCOUNT_ID, None, _BATCH_ID, 0),
    ],
)
def test_should_reject_invalid_cleanup_scope_without_database_reads(
    account_id: str, session_id: str | None, batch_id: str | None, generation: int
) -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    subject, dependencies = _harness(batch, (), now)

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute(account_id, session_id, batch_id, generation)

    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.assert_not_called()
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_session_id.assert_not_called()


@pytest.mark.parametrize('account_id', ['', '  '])
def test_should_reject_deleted_account_cleanup_without_account_id(
    account_id: str,
) -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    subject, dependencies = _harness(batch, (), now)

    with pytest.raises(MentorAttachmentInvalidError):
        subject.execute_for_deleted_account(account_id)

    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_account_id.assert_not_called()


def test_should_treat_missing_batch_as_already_purged() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    subject, dependencies = _harness(batch, (), now)
    dependencies[
        'repositories'
    ].mentor_attachment_batches.find_by_id.return_value = None

    assert subject.execute(_ACCOUNT_ID, None, _BATCH_ID, 1) == 0
    dependencies['storage'].remove.assert_not_called()


def test_should_leave_an_expired_batch_alone_after_it_was_consumed() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now - timedelta(hours=2), now - timedelta(hours=1)
    )
    batch.consumed_by_message_id = '01JMESSAGE000000000000000001'
    attachment = _attachment(
        '01JACTIVE0000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.READY
    )
    subject, dependencies = _harness(batch, (attachment,), now)

    assert subject.execute(_ACCOUNT_ID, None, _BATCH_ID, batch.generation) == 0
    dependencies['storage'].remove.assert_not_called()
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_should_report_private_storage_removal_failure_for_retry() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    batch = MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, None, now, now + timedelta(hours=1)
    )
    removed = _attachment(
        '01JREMOVED000000000000000001', _BATCH_ID, now, MentorAttachmentStatus.REMOVED
    )
    subject, dependencies = _harness(batch, (removed,), now)
    dependencies['storage'].remove.side_effect = ServiceUnavailableError()

    with pytest.raises(MentorAttachmentUnavailableError):
        subject.execute(_ACCOUNT_ID, None, _BATCH_ID, removed.generation)

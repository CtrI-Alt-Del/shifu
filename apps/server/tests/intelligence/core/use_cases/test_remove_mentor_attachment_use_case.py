from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call, create_autospec

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentBatchesRepository,
    MentorAttachmentsRepository,
)
from shifu.intelligence.core.use_cases import RemoveMentorAttachmentUseCase
from shifu.intelligence.core.use_cases.remove_mentor_attachment_use_case import (
    revoke_session_attachments,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    EventsRepository,
    MentorAccessProvider,
)

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_SESSION_ID = '01JSESSION000000000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)


def _batch(*, session_id: str | None = None) -> MentorAttachmentBatch:
    return MentorAttachmentBatch.create(
        _BATCH_ID, _ACCOUNT_ID, session_id, _NOW, _NOW + timedelta(minutes=30)
    )


def _attachment(
    *,
    status: MentorAttachmentStatus = MentorAttachmentStatus.READY,
    generation: int = 1,
    session_id: str | None = _SESSION_ID,
) -> MentorAttachment:
    attachment = MentorAttachment.create(
        _ATTACHMENT_ID,
        _ACCOUNT_ID,
        _BATCH_ID,
        'upload-key',
        'arquivo.txt',
        'text/plain',
        20,
        'a' * 64,
        f'mentor-attachments/{_ATTACHMENT_ID}/{generation}/original',
        _NOW,
    )
    attachment.status = status
    attachment.session_id = session_id
    attachment.generation = generation
    return attachment


class MentorAttachmentRemovalTestSetup:
    database: Mock
    repositories: Mock
    clock: Mock
    access: Mock
    now: datetime
    grant: MentorAccessGrant

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.repositories.mentor_attachment_batches = create_autospec(
            MentorAttachmentBatchesRepository, instance=True
        )
        self.repositories.mentor_attachments = create_autospec(
            MentorAttachmentsRepository, instance=True
        )
        self.repositories.events = create_autospec(EventsRepository, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = _NOW
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.grant = MentorAccessGrant(
            account_id=_ACCOUNT_ID,
            access_revision='revision-1',
            operation_key='operation-1',
        )
        self.access.authorize.return_value = self.grant


class TestRemoveMentorAttachmentUseCase(MentorAttachmentRemovalTestSetup):
    def test_should_revoke_attachment_and_queue_scoped_cleanup(self) -> None:
        batch = _batch()
        attachment = _attachment()
        self.repositories.mentor_attachment_batches.find_by_id.return_value = batch
        self.repositories.mentor_attachments.find_by_id.return_value = attachment
        subject = RemoveMentorAttachmentUseCase(self.database, self.clock, self.access)

        subject.execute(_ACCOUNT_ID, _BATCH_ID, _ATTACHMENT_ID)

        self.access.authorize.assert_called_once_with(_ACCOUNT_ID, _ATTACHMENT_ID)
        self.access.assert_current.assert_has_calls(
            [call(self.grant), call(self.grant)]
        )
        self.repositories.mentor_attachment_batches.find_by_id.assert_called_once_with(
            _BATCH_ID, for_update=True
        )
        self.repositories.mentor_attachments.find_by_id.assert_called_once_with(
            _ATTACHMENT_ID, for_update=True
        )
        assert attachment.status is MentorAttachmentStatus.REMOVED
        assert attachment.generation == 2
        self.repositories.mentor_attachments.update.assert_called_once_with(attachment)
        cleanup = self.repositories.events.add.call_args.args[0]
        assert cleanup.payload.account_id == _ACCOUNT_ID
        assert cleanup.payload.session_id is None
        assert cleanup.payload.batch_id == _BATCH_ID
        assert cleanup.payload.deletion_generation == attachment.generation


class TestRevokeSessionAttachments(MentorAttachmentRemovalTestSetup):
    def test_should_revoke_all_active_attachments_and_queue_batch_cleanup(self) -> None:
        removed = _attachment(status=MentorAttachmentStatus.REMOVED)
        active = _attachment(generation=3)
        batch = _batch(session_id=_SESSION_ID)
        self.repositories.mentor_attachments.find_by_session_id.return_value = (
            removed,
            active,
        )
        self.repositories.mentor_attachment_batches.find_by_session_id.return_value = (
            batch,
        )

        revoke_session_attachments(
            self.repositories, self.access, _ACCOUNT_ID, _SESSION_ID, self.now
        )

        self.access.authorize.assert_called_once_with(_ACCOUNT_ID, _SESSION_ID)
        self.access.assert_current.assert_has_calls(
            [call(self.grant), call(self.grant)]
        )
        self.repositories.mentor_attachments.find_by_session_id.assert_called_once_with(
            _ACCOUNT_ID, _SESSION_ID
        )
        self.repositories.mentor_attachment_batches.find_by_session_id.assert_called_once_with(
            _ACCOUNT_ID, _SESSION_ID
        )
        assert removed.status is MentorAttachmentStatus.REMOVED
        assert active.status is MentorAttachmentStatus.REMOVED
        self.repositories.mentor_attachments.update.assert_called_once_with(active)
        assert batch.revoked_at == self.now
        cleanup = self.repositories.events.add.call_args.args[0]
        assert cleanup.payload.account_id == _ACCOUNT_ID
        assert cleanup.payload.session_id is None
        assert cleanup.payload.batch_id == batch.id
        assert cleanup.payload.deletion_generation == batch.generation

    def test_should_queue_session_cleanup_with_the_latest_attachment_generation(
        self,
    ) -> None:
        attachment = _attachment(generation=4)
        self.repositories.mentor_attachments.find_by_session_id.return_value = (
            attachment,
        )
        self.repositories.mentor_attachment_batches.find_by_session_id.return_value = ()

        revoke_session_attachments(
            self.repositories, self.access, _ACCOUNT_ID, _SESSION_ID, self.now
        )

        cleanup = self.repositories.events.add.call_args.args[0]
        assert cleanup.payload.account_id == _ACCOUNT_ID
        assert cleanup.payload.session_id == _SESSION_ID
        assert cleanup.payload.batch_id is None
        assert cleanup.payload.deletion_generation == 5

    def test_should_not_queue_cleanup_when_nothing_changed(self) -> None:
        self.repositories.mentor_attachments.find_by_session_id.return_value = ()
        self.repositories.mentor_attachment_batches.find_by_session_id.return_value = ()

        revoke_session_attachments(
            self.repositories, self.access, _ACCOUNT_ID, _SESSION_ID, self.now
        )

        self.repositories.mentor_attachments.update.assert_not_called()
        self.repositories.mentor_attachment_batches.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

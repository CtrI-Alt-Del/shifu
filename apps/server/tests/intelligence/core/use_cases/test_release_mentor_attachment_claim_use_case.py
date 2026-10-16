from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.domain.entities import MentorAttachment
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorAttachmentsRepository,
)
from shifu.intelligence.core.use_cases import ReleaseMentorAttachmentClaimUseCase

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_BATCH_ID = '01JBATCH00000000000000000001'
_EXECUTION_OWNER = 'preparation-worker'
_NOW = datetime(2026, 10, 10, tzinfo=UTC)
_Harness = tuple[ReleaseMentorAttachmentClaimUseCase, dict[str, Any]]


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
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.mentor_attachments.find_by_id.return_value = attachment
    subject = ReleaseMentorAttachmentClaimUseCase(database)
    return subject, {'attachment': attachment, 'repositories': repositories}


def test_release_clears_only_the_matching_claim(harness: _Harness) -> None:
    subject, dependencies = harness

    subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    attachment = dependencies['attachment']
    assert attachment.status is MentorAttachmentStatus.PROCESSING
    assert attachment.execution_owner is None
    assert attachment.claim_expires_at is None
    dependencies['repositories'].mentor_attachments.update.assert_called_once_with(
        attachment
    )


@pytest.mark.parametrize(
    'generation,owner', [(2, _EXECUTION_OWNER), (1, 'stale-worker')]
)
def test_release_ignores_a_replaced_generation_or_foreign_owner(
    harness: _Harness, generation: int, owner: str
) -> None:
    subject, dependencies = harness

    subject.execute(_ATTACHMENT_ID, generation, owner)

    assert dependencies['attachment'].execution_owner == _EXECUTION_OWNER
    assert dependencies['attachment'].claim_expires_at == _NOW + timedelta(minutes=4)
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_release_does_not_change_a_non_processing_attachment(harness: _Harness) -> None:
    subject, dependencies = harness
    dependencies['attachment'].transition(
        MentorAttachmentStatus.FAILED, 'analysis_unavailable'
    )

    subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    assert dependencies['attachment'].status is MentorAttachmentStatus.FAILED
    dependencies['repositories'].mentor_attachments.update.assert_not_called()


def test_release_is_idempotent_when_the_attachment_is_missing(
    harness: _Harness,
) -> None:
    subject, dependencies = harness
    dependencies['repositories'].mentor_attachments.find_by_id.return_value = None

    subject.execute(_ATTACHMENT_ID, 1, _EXECUTION_OWNER)

    dependencies['repositories'].mentor_attachments.update.assert_not_called()

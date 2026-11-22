from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import ReadMentorAttachmentFileUseCase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    FileStorageProvider,
    IdentifierProvider,
    MentorAccessProvider,
)

_ACCOUNT_ID = '01JACCOUNT000000000000000001'
_SESSION_ID = '01JSESSION000000000000000001'
_ATTACHMENT_ID = '01JATTACHMENT00000000000001'
_OBJECT_KEY = f'mentor-attachments/{_ATTACHMENT_ID}/1/original'


def test_reads_storage_only_inside_account_activity_gate() -> None:
    database = create_autospec(IntelligenceDatabase, instance=True)
    repositories = create_autospec(IntelligenceDatabaseRepositories, instance=True)
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.mentor_sessions.find_by_id_for_update.return_value = object()
    attachment = SimpleNamespace(
        account_id=_ACCOUNT_ID,
        session_id=_SESSION_ID,
        message_id='01JMENTORMESSAGE000000000001',
        status=MentorAttachmentStatus.READY,
        media_type='image/png',
        preview_key=None,
        object_key=_OBJECT_KEY,
        generation=1,
        filename='work.png',
    )
    repositories.mentor_attachments.find_by_id.return_value = attachment
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=_ACCOUNT_ID,
        access_revision='revision',
        operation_key='operation',
    )
    storage = create_autospec(FileStorageProvider, instance=True)
    storage.read.return_value = b'private attachment bytes'
    activity = create_autospec(AccountActivityProvider, instance=True)
    activity.activity.return_value = nullcontext()
    identifiers = create_autospec(IdentifierProvider, instance=True)
    identifiers.generate.return_value = 'operation-id'

    result = ReadMentorAttachmentFileUseCase(
        database, identifiers, access, storage, activity
    ).execute(_ACCOUNT_ID, _SESSION_ID, _ATTACHMENT_ID, preview=False)

    assert result.content == b'private attachment bytes'
    activity.activity.assert_called_once_with(_ACCOUNT_ID)
    storage.read.assert_called_once_with(_OBJECT_KEY)


def test_revoked_account_gate_blocks_storage_read() -> None:
    database = create_autospec(IntelligenceDatabase, instance=True)
    access = create_autospec(MentorAccessProvider, instance=True)
    storage = create_autospec(FileStorageProvider, instance=True)
    activity = create_autospec(AccountActivityProvider, instance=True)
    activity.activity.side_effect = RuntimeError('revoked')
    identifiers = create_autospec(IdentifierProvider, instance=True)

    with pytest.raises(RuntimeError, match='revoked'):
        ReadMentorAttachmentFileUseCase(
            database, identifiers, access, storage, activity
        ).execute(_ACCOUNT_ID, _SESSION_ID, _ATTACHMENT_ID, preview=False)

    database.transaction.assert_not_called()
    storage.read.assert_not_called()

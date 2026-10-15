from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.messaging.inngest.inngest_broker import InngestBroker
from shifu.shared.pipes import FileStoragePipe, SharedPipe
from tests.intelligence.server.controllers.conftest import (
    MENTOR_ACCOUNT,
    MentorAttachmentExtractorStub,
    MentorAttachmentStorageStub,
    configure_mentor_access,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from fastapi import FastAPI
    from tests.fixtures.postgres_fixture import PostgresDatabase

_MAX_FILE_SIZE = 10_000_000


@pytest.fixture
def mentor_attachment_http_boundary(
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, MentorAttachmentStorageStub]]:
    monkeypatch.setattr('shifu.app.InngestBroker', create_autospec(InngestBroker))
    app: FastAPI = FastAPIApp.register(postgres_database.engine)
    configure_mentor_access(app)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: MENTOR_ACCOUNT
    storage = MentorAttachmentStorageStub()
    app.dependency_overrides[FileStoragePipe.get_file_storage_provider] = lambda: (
        storage
    )
    app.dependency_overrides[
        IntelligencePipe.get_mentor_attachment_extractor_provider
    ] = MentorAttachmentExtractorStub

    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client, storage


def _create_batch(client: TestClient) -> str:
    response = client.post('/intelligence/mentor-attachment-batches', json={})
    assert response.status_code == 201
    return response.json()['batch_id']


class TestMentorAttachmentsController:
    def test_registered_batch_lifecycle_uploads_lists_and_removes_private_file(
        self,
        mentor_attachment_http_boundary: tuple[TestClient, MentorAttachmentStorageStub],
    ) -> None:
        client, storage = mentor_attachment_http_boundary
        batch_id = _create_batch(client)
        upload = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': ('notes.txt', b'private notes', 'text/plain')},
        )

        assert upload.status_code == 201
        assert upload.headers['cache-control'] == 'private, no-store'
        attachment_id = upload.json()['attachment_id']
        assert len(storage.objects) == 1

        batch = client.get(f'/intelligence/mentor-attachment-batches/{batch_id}')
        assert batch.status_code == 200
        assert batch.headers['cache-control'] == 'private, no-store'
        assert batch.json()['attachments'][0]['attachment_id'] == attachment_id

        removed = client.delete(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}'
        )

        assert removed.status_code == 204
        assert removed.headers['cache-control'] == 'private, no-store'
        assert len(storage.objects) == 1
        removed_batch = client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert removed_batch.json()['attachments'][0]['status'] == 'removed'

    def test_registered_create_batch_rejects_a_malformed_session_reference(
        self,
        mentor_attachment_http_boundary: tuple[TestClient, MentorAttachmentStorageStub],
    ) -> None:
        client, _storage = mentor_attachment_http_boundary

        response = client.post(
            '/intelligence/mentor-attachment-batches',
            json={'session_id': 'not-a-ulid'},
        )

        assert response.status_code == 422

    def test_registered_upload_rejects_a_file_over_the_size_limit_without_writes(
        self,
        mentor_attachment_http_boundary: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, storage = mentor_attachment_http_boundary
        batch_id = _create_batch(client)
        response = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={
                'file': (
                    'document.txt',
                    b'x' * (_MAX_FILE_SIZE + 1),
                    'text/plain',
                )
            },
        )

        with SqlalchemyIntelligenceDatabase(
            engine=postgres_database.engine
        ).transaction() as repositories:
            persisted = repositories.mentor_attachments.find_by_batch_id(batch_id)

        assert response.status_code == 413
        assert persisted == ()
        assert storage.objects == {}

    def test_registered_upload_rejects_a_malformed_batch_path_without_writes(
        self,
        mentor_attachment_http_boundary: tuple[TestClient, MentorAttachmentStorageStub],
    ) -> None:
        client, storage = mentor_attachment_http_boundary
        response = client.post(
            '/intelligence/mentor-attachment-batches/not-a-ulid/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': ('document.txt', b'valid content', 'text/plain')},
        )

        assert response.status_code == 422
        assert storage.objects == {}

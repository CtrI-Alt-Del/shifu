from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import uuid4

import boto3
import pytest
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

from tests.intelligence.server.controllers.mentor_response_scenarios import (
    complete_response,
    create_session,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi.testclient import TestClient
    from tests.fixtures.postgres_fixture import PostgresDatabase


class _ObjectBody:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self.closed = False

    def read(self) -> bytes:
        return self._content

    def close(self) -> None:
        self.closed = True


class _ObjectStorageService:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.put_requests: list[dict[str, object]] = []
        self.get_requests: list[dict[str, object]] = []
        self.read_bodies: list[_ObjectBody] = []
        self.fail_put = False
        self.fail_get = False

    def put_object(self, **request: object) -> object:
        self.put_requests.append(request)
        if self.fail_put:
            raise RuntimeError('private object storage endpoint')
        key = cast('str', request['Key'])
        body = cast('bytes', request['Body'])
        media_type = cast('str', request['ContentType'])
        self.objects[key] = (body, media_type)
        return {}

    def get_object(self, **request: object) -> dict[str, object]:
        self.get_requests.append(request)
        if self.fail_get:
            raise RuntimeError('private object storage endpoint')
        key = cast('str', request['Key'])
        body = _ObjectBody(self.objects[key][0])
        self.read_bodies.append(body)
        return {'Body': body}

    def delete_object(self, **request: object) -> object:
        self.objects.pop(cast('str', request['Key']), None)
        return {}

    def close(self) -> None:
        return None


@pytest.fixture
def mentor_client_with_object_storage(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, _ObjectStorageService]]:
    storage = _ObjectStorageService()

    def create_storage_client(
        *_args: object, **_kwargs: object
    ) -> _ObjectStorageService:
        return storage

    monkeypatch.setattr(boto3, 'client', create_storage_client)
    client = cast('TestClient', request.getfixturevalue('mentor_client'))
    yield client, storage


def _mark_attachment_ready(
    database: PostgresDatabase,
    attachment_id: str,
    content: str,
) -> None:
    with SqlalchemyIntelligenceDatabase(database.engine).transaction() as repositories:
        attachment = repositories.mentor_attachments.find_by_id(attachment_id)
        assert attachment is not None
        chunk = MentorAttachmentChunk(
            chunk_id=SystemIdentifierProvider().generate(),
            attachment_id=attachment.id,
            generation=attachment.generation,
            page_number=None,
            locator=f'chars:1-{len(content)}#1',
            content=content,
        )
        attachment.apply_extraction(
            MentorAttachmentExtraction(
                chunks=(chunk,),
                analyzed_pages=(),
                illegible_pages=(),
                uninterpreted_pages=(),
            ),
            MentorAttachmentStatus.READY,
        )
        repositories.mentor_attachments.update(attachment)
        repositories.mentor_attachment_chunks.add_many((chunk,))


def _prepare_attachment_for_download(
    client: TestClient,
    database: PostgresDatabase,
    storage: _ObjectStorageService,
) -> tuple[str, str, bytes]:
    session_id, attempt_id, message_id = create_session(client)
    complete_response(database, session_id, attempt_id, message_id)
    batch = client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch.status_code == 201
    batch_id = batch.json()['batch_id']
    content = b'Private attachment storage boundary.'
    uploaded = client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('notes.txt', content, 'text/plain')},
    )
    assert uploaded.status_code == 201
    attachment_id = uploaded.json()['attachment_id']
    _mark_attachment_ready(database, attachment_id, content.decode())
    submitted = client.post(
        f'/intelligence/mentor-sessions/{session_id}/messages',
        json={
            'submission_key': str(uuid4()),
            'content': 'Explique o conteúdo do arquivo.',
            'attachment_batch_id': batch_id,
            'attachment_ids': [attachment_id],
        },
    )
    assert submitted.status_code == 202
    assert len(storage.put_requests) == 1
    return session_id, attachment_id, content


def test_registered_attachment_routes_use_private_object_storage(
    mentor_client_with_object_storage: tuple[TestClient, _ObjectStorageService],
    postgres_database: PostgresDatabase,
) -> None:
    client, storage = mentor_client_with_object_storage
    session_id, attachment_id, content = _prepare_attachment_for_download(
        client, postgres_database, storage
    )
    downloaded = client.get(
        f'/intelligence/mentor-sessions/{session_id}/attachments/{attachment_id}/file'
    )

    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers['cache-control'] == 'private, no-store'
    assert len(storage.put_requests) == 1
    put_request = storage.put_requests[0]
    assert put_request['Body'] == content
    assert put_request['ContentType'] == 'text/plain'
    assert 'ACL' not in put_request
    assert storage.get_requests == [
        {'Bucket': put_request['Bucket'], 'Key': put_request['Key']}
    ]
    assert storage.read_bodies[0].closed is True


def test_registered_download_sanitizes_object_storage_failures(
    mentor_client_with_object_storage: tuple[TestClient, _ObjectStorageService],
    postgres_database: PostgresDatabase,
) -> None:
    client, storage = mentor_client_with_object_storage
    session_id, attachment_id, _ = _prepare_attachment_for_download(
        client, postgres_database, storage
    )
    storage.fail_get = True

    response = client.get(
        f'/intelligence/mentor-sessions/{session_id}/attachments/{attachment_id}/file'
    )

    assert response.status_code == 503
    assert 'private object storage endpoint' not in response.text


def test_registered_upload_sanitizes_object_storage_failures(
    mentor_client_with_object_storage: tuple[TestClient, _ObjectStorageService],
) -> None:
    client, storage = mentor_client_with_object_storage
    storage.fail_put = True
    batch = client.post('/intelligence/mentor-attachment-batches', json={})
    assert batch.status_code == 201

    response = client.post(
        f'/intelligence/mentor-attachment-batches/{batch.json()["batch_id"]}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('notes.txt', b'private bytes', 'text/plain')},
    )

    assert response.status_code == 201
    assert response.json()['status'] == 'failed'
    assert response.json()['failure_code'] == 'storage_write_failed'
    assert 'private object storage endpoint' not in response.text
    assert len(storage.put_requests) == 1


class TestMentorAttachmentStorageHttpBoundary:
    def test_registered_download_does_not_read_an_uploading_attachment(
        self,
        mentor_client_with_object_storage: tuple[TestClient, _ObjectStorageService],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, storage = mentor_client_with_object_storage
        session_id, attempt_id, message_id = create_session(client)
        complete_response(postgres_database, session_id, attempt_id, message_id)
        batch = client.post(
            '/intelligence/mentor-attachment-batches',
            json={'session_id': session_id},
        )
        assert batch.status_code == 201
        batch_id = batch.json()['batch_id']
        uploaded = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': ('notes.txt', b'Not yet ready.', 'text/plain')},
        )
        assert uploaded.status_code == 201
        attachment_id = uploaded.json()['attachment_id']

        response = client.get(
            f'/intelligence/mentor-sessions/{session_id}/attachments/{attachment_id}/file'
        )
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted = repositories.mentor_attachments.find_by_id(attachment_id)

        assert response.status_code == 404
        assert response.json()['code'] == 'not_found'
        assert storage.get_requests == []
        assert persisted is not None
        assert persisted.status is MentorAttachmentStatus.UPLOADING

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from shifu.app import FastAPIApp
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.messaging.inngest.inngest_broker import InngestBroker
from shifu.shared.pipes import FileStoragePipe, SharedPipe
from tests.fixtures.intelligence_fixture import (
    MENTOR_ACCOUNT,
    MentorAttachmentExtractorStub,
    MentorAttachmentStorageStub,
    configure_mentor_access,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from fastapi import FastAPI
    from tests.fixtures.postgres_fixture import PostgresDatabase

_MAX_FILE_SIZE = 2_000_000


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


@pytest.fixture
def mentor_attachment_local_extractor_http_boundary(
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
        assert response.json() == {
            'code': 'malformed_attachment',
            'message': 'O arquivo não é válido ou não está disponível.',
        }

    @pytest.mark.parametrize(
        ('method', 'path'),
        [
            ('GET', '/intelligence/mentor-attachment-batches/not-a-ulid'),
            (
                'DELETE',
                '/intelligence/mentor-attachment-batches/not-a-ulid/attachments/'
                + '0' * 25
                + '1',
            ),
            (
                'GET',
                '/intelligence/mentor-sessions/not-a-ulid/attachments/'
                + '0' * 25
                + '1/file',
            ),
        ],
    )
    def test_registered_routes_reject_malformed_resource_ids(
        self,
        mentor_attachment_http_boundary: tuple[TestClient, MentorAttachmentStorageStub],
        method: str,
        path: str,
    ) -> None:
        client, _storage = mentor_attachment_http_boundary

        response = client.request(method, path)

        assert response.status_code == 422
        assert response.json()['code'] == 'validation_error'

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
        assert response.json() == {
            'code': 'attachment_too_large',
            'message': 'O arquivo excede o limite de 2 MB.',
        }
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
        assert response.json()['code'] == 'validation_error'
        assert storage.objects == {}

    def test_registered_upload_rejects_non_decimal_content_length_after_middleware(
        self,
        mentor_attachment_http_boundary: tuple[TestClient, MentorAttachmentStorageStub],
    ) -> None:
        client, storage = mentor_attachment_http_boundary
        batch_id = _create_batch(client)
        boundary = 'mentor-attachment-boundary'
        upload_key = str(uuid4()).encode()
        body = (
            f'--{boundary}\r\n'.encode()
            + b'Content-Disposition: form-data; name="upload_key"\r\n\r\n'
            + upload_key
            + f'\r\n--{boundary}\r\n'.encode()
            + b'Content-Disposition: form-data; name="file"; filename="notes.txt"\r\n'
            + b'Content-Type: text/plain\r\n\r\nnotes\r\n'
            + f'--{boundary}--\r\n'.encode()
        )

        response = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            content=body,
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': f'+{len(body)}',
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            'code': 'malformed_attachment',
            'message': 'O arquivo não é válido ou não está disponível.',
        }
        assert storage.objects == {}

    def test_registered_upload_uses_the_local_extractor_for_text_and_image_validation(
        self,
        mentor_attachment_local_extractor_http_boundary: tuple[
            TestClient, MentorAttachmentStorageStub
        ],
    ) -> None:
        client, storage = mentor_attachment_local_extractor_http_boundary
        batch_id = _create_batch(client)
        image_buffer = BytesIO()
        image = Image.new('RGB', (2, 2), color='white')
        image.save(image_buffer, format='PNG')
        image.close()
        jpeg_buffer = BytesIO()
        jpeg = Image.new('RGB', (2, 2), color='black')
        jpeg.save(jpeg_buffer, format='JPEG')
        jpeg.close()
        pdf_buffer = BytesIO()
        pdf_writer = PdfWriter()
        pdf_writer.add_blank_page(width=72, height=72)
        pdf_writer.write(pdf_buffer)
        valid_uploads = (
            ('notes.txt', b'plain notes', 'text/plain'),
            ('long-notes.txt', b'a' * 200_001, 'text/plain'),
            ('diagram.png', image_buffer.getvalue(), 'image/png'),
            ('worksheet.pdf', pdf_buffer.getvalue(), 'application/pdf'),
        )

        for filename, content, media_type in valid_uploads:
            response = client.post(
                f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
                data={'upload_key': str(uuid4())},
                files={'file': (filename, content, media_type)},
            )
            assert response.status_code == 201, response.text

        invalid_uploads = (
            ('invalid-encoding.txt', b'\xff', 'text/plain'),
            ('mismatched.png', jpeg_buffer.getvalue(), 'image/png'),
            ('corrupt.png', b'not an image', 'image/png'),
            ('malformed.pdf', b'%PDF-1.4\nnot a PDF', 'application/pdf'),
        )
        object_count = len(storage.objects)

        for filename, content, media_type in invalid_uploads:
            response = client.post(
                f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
                data={'upload_key': str(uuid4())},
                files={'file': (filename, content, media_type)},
            )
            assert response.status_code == 422, (filename, response.text)

        assert len(storage.objects) == object_count

    def test_registered_upload_validates_csv_json_and_blank_text_with_local_extractor(
        self,
        mentor_attachment_local_extractor_http_boundary: tuple[
            TestClient, MentorAttachmentStorageStub
        ],
    ) -> None:
        client, storage = mentor_attachment_local_extractor_http_boundary
        batch_id = _create_batch(client)
        empty_pdf = BytesIO()
        PdfWriter().write(empty_pdf)
        encrypted_pdf_writer = PdfWriter()
        encrypted_pdf_writer.add_blank_page(width=72, height=72)
        encrypted_pdf_writer.encrypt('test-password')
        encrypted_pdf = BytesIO()
        encrypted_pdf_writer.write(encrypted_pdf)
        uploads = (
            ('lesson.csv', b'topic,count\nmath,2\n', 'text/csv', 201),
            ('lesson.json', b'{"topic":"math"}', 'application/json', 201),
            ('blank.txt', b' \n\t', 'text/plain', 422),
            ('malformed.csv', b'"unterminated', 'text/csv', 422),
            ('malformed.json', b'{broken}', 'application/json', 422),
            (
                'oversized.json',
                b'{"text":"' + b'x' * 1_000_001 + b'"}',
                'application/json',
                422,
            ),
            ('empty.pdf', empty_pdf.getvalue(), 'application/pdf', 422),
            ('encrypted.pdf', encrypted_pdf.getvalue(), 'application/pdf', 422),
        )

        for filename, content, media_type, expected_status in uploads:
            response = client.post(
                f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
                data={'upload_key': str(uuid4())},
                files={'file': (filename, content, media_type)},
            )
            assert response.status_code == expected_status, (filename, response.text)

        assert len(storage.objects) == 2

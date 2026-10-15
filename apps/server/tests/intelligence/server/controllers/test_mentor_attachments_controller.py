from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.fixtures.postgres_fixture import PostgresDatabase

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.intelligence.server.controllers.conftest import (
    MENTOR_ACCOUNT,
    MentorAttachmentStorageStub,
)
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    complete_response,
    create_session,
)

_UPLOAD_PATH = f'/intelligence/mentor-attachment-batches/{"0" * 25}1/attachments'
_MAX_MULTIPART_BYTES = 10_064_000


def _create_attachment_batch(client: TestClient, session_id: str) -> str:
    response = client.post(
        '/intelligence/mentor-attachment-batches', json={'session_id': session_id}
    )

    assert response.status_code == 201
    assert response.headers['cache-control'] == 'private, no-store'
    return response.json()['batch_id']


def _upload_text_attachment(
    client: TestClient, batch_id: str, *, filename: str = 'notes.txt'
) -> tuple[str, str]:
    upload_key = str(uuid4())
    response = client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': upload_key},
        files={'file': (filename, b'Attachment content for the Mentor.', 'text/plain')},
    )

    assert response.status_code == 201
    assert response.headers['cache-control'] == 'private, no-store'
    return response.json()['attachment_id'], upload_key


def _mark_attachment_ready(
    postgres_database: PostgresDatabase,
    attachment_id: str,
    *,
    image: bool = False,
) -> None:
    with SqlalchemyIntelligenceDatabase(
        postgres_database.engine
    ).transaction() as repositories:
        attachment = repositories.mentor_attachments.find_by_id(attachment_id)
        assert attachment is not None
        chunk = MentorAttachmentChunk(
            chunk_id=SystemIdentifierProvider().generate(),
            attachment_id=attachment.id,
            generation=attachment.generation,
            page_number=1 if image else None,
            locator='page:1/chars:1-18#1' if image else 'chars:1-18#1',
            content='Texto extraído para busca.',
        )
        extraction = MentorAttachmentExtraction(
            chunks=(chunk,),
            analyzed_pages=(1,) if image else (),
            illegible_pages=(),
            uninterpreted_pages=(),
        )
        # Async preparation owns this transition; seed its persisted result so
        # the following assertions remain on the registered HTTP boundary.
        attachment.apply_extraction(extraction, MentorAttachmentStatus.READY)
        repositories.mentor_attachments.update(attachment)
        repositories.mentor_attachment_chunks.add_many((chunk,))


def _seed_attachment_status(
    postgres_database: PostgresDatabase,
    attachment_id: str,
    status: MentorAttachmentStatus,
) -> None:
    with SqlalchemyIntelligenceDatabase(
        postgres_database.engine
    ).transaction() as repositories:
        attachment = repositories.mentor_attachments.find_by_id(attachment_id)
        assert attachment is not None
        now = datetime.now(UTC)

        if status is MentorAttachmentStatus.PROCESSING:
            attachment.claim('registered-test-worker', now, now + timedelta(minutes=1))
        else:
            chunk = MentorAttachmentChunk(
                chunk_id=SystemIdentifierProvider().generate(),
                attachment_id=attachment.id,
                generation=attachment.generation,
                page_number=1,
                locator='page:1/chars:1-18#1',
                content='Texto extraído para busca.',
            )
            extraction = MentorAttachmentExtraction(
                chunks=(chunk,),
                analyzed_pages=(1,),
                illegible_pages=(),
                uninterpreted_pages=(2,)
                if status is MentorAttachmentStatus.PARTIAL
                else (),
            )
            if status is MentorAttachmentStatus.FAILED:
                attachment.claim(
                    'registered-test-worker', now, now + timedelta(minutes=1)
                )
                attachment.fail_extraction(extraction, 'extraction_failed')
            else:
                attachment.apply_extraction(extraction, status)
                repositories.mentor_attachment_chunks.add_many((chunk,))

        repositories.mentor_attachments.update(attachment)


class TestMentorAttachmentsController:
    def test_create_batch_rejects_malformed_session_without_persisting_a_batch(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, _ = mentor_attachment_client

        response = client.post(
            '/intelligence/mentor-attachment-batches',
            json={'session_id': 'not-a-mentor-session-id'},
        )
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted_batches = (
                repositories.mentor_attachment_batches.find_by_account_id(
                    MENTOR_ACCOUNT.account_id
                )
            )

        assert response.status_code == 422
        assert response.json()['detail'] == {
            'code': 'malformed_attachment',
            'message': 'O arquivo não é válido ou não está disponível.',
        }
        assert persisted_batches == ()

    def test_missing_batch_and_attachment_return_safe_not_found_responses(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, _ = mentor_attachment_client
        created = client.post('/intelligence/mentor-attachment-batches', json={})
        assert created.status_code == 201
        batch_id = created.json()['batch_id']
        missing_id = '0' * 26

        missing_batch = client.get(
            f'/intelligence/mentor-attachment-batches/{missing_id}'
        )
        missing_attachment = client.delete(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments/{missing_id}'
        )
        batch = client.get(f'/intelligence/mentor-attachment-batches/{batch_id}')
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted_missing = repositories.mentor_attachments.find_by_id(missing_id)

        assert missing_batch.status_code == 404
        assert missing_batch.json()['code'] == 'not_found'
        assert missing_attachment.status_code == 404
        assert missing_attachment.json()['code'] == 'not_found'
        assert batch.status_code == 200
        assert batch.json()['attachments'] == []
        assert persisted_missing is None

    def test_batch_readback_preserves_attachment_statuses_and_pages(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, _ = mentor_attachment_client
        created = client.post('/intelligence/mentor-attachment-batches', json={})
        assert created.status_code == 201
        batch_id = created.json()['batch_id']
        attachment_ids = {
            status: _upload_text_attachment(
                client, batch_id, filename=f'{status.value}.txt'
            )[0]
            for status in (
                MentorAttachmentStatus.UPLOADING,
                MentorAttachmentStatus.PROCESSING,
                MentorAttachmentStatus.READY,
                MentorAttachmentStatus.PARTIAL,
                MentorAttachmentStatus.FAILED,
            )
        }
        for status in (
            MentorAttachmentStatus.PROCESSING,
            MentorAttachmentStatus.READY,
            MentorAttachmentStatus.PARTIAL,
            MentorAttachmentStatus.FAILED,
        ):
            _seed_attachment_status(postgres_database, attachment_ids[status], status)

        batch = client.get(f'/intelligence/mentor-attachment-batches/{batch_id}')
        attachments_by_status = {
            attachment['status']: attachment
            for attachment in batch.json()['attachments']
        }
        assert batch.status_code == 200
        assert attachments_by_status['uploading']['filename'] == 'uploading.txt'
        assert attachments_by_status['processing']['filename'] == 'processing.txt'
        assert attachments_by_status['ready']['analyzed_pages'] == [1]
        assert attachments_by_status['ready']['uninterpreted_pages'] == []
        assert attachments_by_status['partial']['analyzed_pages'] == [1]
        assert attachments_by_status['partial']['uninterpreted_pages'] == [2]
        assert attachments_by_status['failed']['failure_code'] == 'extraction_failed'

        removed_id = attachment_ids[MentorAttachmentStatus.PROCESSING]
        removed = client.delete(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments/{removed_id}'
        )
        batch_after_removal = client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted = {
                status: repositories.mentor_attachments.find_by_id(attachment_id)
                for status, attachment_id in attachment_ids.items()
            }
            active_count = repositories.mentor_attachments.count_active_in_batch(
                batch_id
            )
        persisted_processing = persisted[MentorAttachmentStatus.PROCESSING]

        assert removed.status_code == 204
        assert batch_after_removal.status_code == 200
        assert (
            next(
                attachment
                for attachment in batch_after_removal.json()['attachments']
                if attachment['attachment_id'] == removed_id
            )['status']
            == 'removed'
        )
        assert persisted_processing is not None
        assert persisted_processing.status is MentorAttachmentStatus.REMOVED
        assert all(attachment is not None for attachment in persisted.values())
        assert active_count == 4

    def test_should_reject_declared_oversize_before_multipart_parsing(
        self, client: TestClient
    ) -> None:
        response = client.post(
            _UPLOAD_PATH,
            content=b'invalid multipart body',
            headers={
                'content-type': 'multipart/form-data; boundary=unused',
                'content-length': str(_MAX_MULTIPART_BYTES + 1),
            },
        )

        assert response.status_code == 413
        assert response.json()['code'] == 'attachment_too_large'

    def test_should_reject_chunked_oversize_before_multipart_parsing(
        self, client: TestClient
    ) -> None:
        response = client.post(
            _UPLOAD_PATH,
            content=iter(
                (
                    b'x' * 6_000_000,
                    b'x' * (_MAX_MULTIPART_BYTES - 6_000_000 + 1),
                )
            ),
            headers={'content-type': 'multipart/form-data; boundary=unused'},
        )

        assert response.status_code == 413
        assert response.json()['code'] == 'attachment_too_large'

    def test_registered_routes_persist_upload_retry_batch_view_and_removal(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, storage = mentor_attachment_client
        session_id, attempt_id, message_id = create_session(client)
        complete_response(postgres_database, session_id, attempt_id, message_id)
        batch_id = _create_attachment_batch(client, session_id)

        attachment_id, upload_key = _upload_text_attachment(client, batch_id)
        uploaded = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': upload_key},
            files={
                'file': (
                    'notes.txt',
                    b'Attachment content for the Mentor.',
                    'text/plain',
                )
            },
        )
        batch = client.get(f'/intelligence/mentor-attachment-batches/{batch_id}')

        assert uploaded.status_code == 200
        assert uploaded.json()['attachment_id'] == attachment_id
        assert len(storage.objects) == 1
        assert batch.status_code == 200
        assert batch.headers['cache-control'] == 'private, no-store'
        assert batch.json()['batch_id'] == batch_id
        assert batch.json()['attachments'] == [
            {
                'attachment_id': attachment_id,
                'filename': 'notes.txt',
                'media_type': 'text/plain',
                'size_bytes': len(b'Attachment content for the Mentor.'),
                'status': 'uploading',
                'failure_code': None,
                'analyzed_pages': [],
                'illegible_pages': [],
                'uninterpreted_pages': [],
            }
        ]

        removed = client.delete(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}'
        )
        removed_batch = client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted = repositories.mentor_attachments.find_by_id(attachment_id)

        assert removed.status_code == 204
        assert removed.headers['cache-control'] == 'private, no-store'
        assert removed_batch.json()['attachments'][0]['status'] == 'removed'
        assert persisted is not None
        assert persisted.account_id == MENTOR_ACCOUNT.account_id
        assert persisted.status is MentorAttachmentStatus.REMOVED

    def test_registered_upload_accepts_multipart_without_content_length(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, storage = mentor_attachment_client
        created = client.post('/intelligence/mentor-attachment-batches', json={})
        assert created.status_code == 201
        batch_id = created.json()['batch_id']
        upload_key = str(uuid4())
        boundary = 'mentor-attachment-stream-boundary'
        content = b'Chunked upload content.'
        body = (
            (
                f'--{boundary}\r\n'
                'Content-Disposition: form-data; name="file"; filename="streamed.txt"\r\n'
                'Content-Type: text/plain\r\n\r\n'
            ).encode()
            + content
            + (
                f'\r\n--{boundary}\r\n'
                'Content-Disposition: form-data; name="upload_key"\r\n\r\n'
                f'{upload_key}\r\n'
                f'--{boundary}--\r\n'
            ).encode()
        )

        response = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            content=iter((body[:40], body[40:])),
            headers={'content-type': f'multipart/form-data; boundary={boundary}'},
        )
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted = repositories.mentor_attachments.find_by_upload_key(
                batch_id, upload_key
            )

        assert response.status_code == 201
        assert response.json()['filename'] == 'streamed.txt'
        assert response.json()['size_bytes'] == len(content)
        assert len(storage.objects) == 1
        assert persisted is not None
        assert persisted.filename == 'streamed.txt'
        assert persisted.status is MentorAttachmentStatus.UPLOADING

    def test_registered_upload_maps_invalid_attachment_to_safe_http_error(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
    ) -> None:
        client, storage = mentor_attachment_client
        batch = client.post('/intelligence/mentor-attachment-batches', json={})
        assert batch.status_code == 201
        batch_id = batch.json()['batch_id']

        response = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={
                'file': ('payload.bin', b'private input', 'application/octet-stream')
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            'code': 'malformed_attachment',
            'message': 'O arquivo não é válido ou não é compatível.',
        }
        assert storage.objects == {}

    def test_removed_attachment_is_hidden_from_history_and_replay(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, _ = mentor_attachment_client
        session_id, attempt_id, message_id = create_session(client)
        complete_response(postgres_database, session_id, attempt_id, message_id)
        batch_id = _create_attachment_batch(client, session_id)
        attachment_id, _ = _upload_text_attachment(client, batch_id)
        _mark_attachment_ready(postgres_database, attachment_id)
        submission_key = str(uuid4())
        submission = {
            'submission_key': submission_key,
            'content': 'Explique o arquivo anexado.',
            'attachment_batch_id': batch_id,
            'attachment_ids': [attachment_id],
        }

        first_submission = client.post(
            f'/intelligence/mentor-sessions/{session_id}/messages', json=submission
        )
        history_before_removal = client.get(
            f'/intelligence/mentor-sessions/{session_id}'
        )
        assert first_submission.status_code == 202
        assert any(
            attachment['attachment_id'] == attachment_id
            and attachment['status'] == 'ready'
            for message in history_before_removal.json()['messages']['items']
            for attachment in message['attachments']
        )
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
            assert attachment is not None
            attachment.revoke()
            repositories.mentor_attachments.update(attachment)

        replay = client.post(
            f'/intelligence/mentor-sessions/{session_id}/messages', json=submission
        )
        history = client.get(f'/intelligence/mentor-sessions/{session_id}')
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            persisted = repositories.mentor_attachments.find_by_id(attachment_id)

        assert replay.status_code == 409
        assert history.status_code == 200
        assert all(
            attachment['attachment_id'] != attachment_id
            for message in history.json()['messages']['items']
            for attachment in message['attachments']
        )
        assert persisted is not None
        assert persisted.status is MentorAttachmentStatus.REMOVED

    def test_registered_routes_download_and_preview_bound_attachment_files(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, storage = mentor_attachment_client
        session_id, attempt_id, message_id = create_session(client)
        complete_response(postgres_database, session_id, attempt_id, message_id)
        batch_id = _create_attachment_batch(client, session_id)
        attachment_id, _ = _upload_text_attachment(client, batch_id)
        _mark_attachment_ready(postgres_database, attachment_id)

        submitted = client.post(
            f'/intelligence/mentor-sessions/{session_id}/messages',
            json={
                'submission_key': str(uuid4()),
                'content': 'Explique o conteúdo do arquivo.',
                'attachment_batch_id': batch_id,
                'attachment_ids': [attachment_id],
            },
        )
        download = client.get(
            f'/intelligence/mentor-sessions/{session_id}/attachments/{attachment_id}/file'
        )
        rejected_preview = client.get(
            f'/intelligence/mentor-sessions/{session_id}/attachments/{attachment_id}/file',
            params={'preview': 'true'},
        )

        assert submitted.status_code == 202
        assert submitted.headers['cache-control'] == 'private, no-store'
        assert download.status_code == 200
        assert download.content == storage.objects[next(iter(storage.objects))][0]
        assert download.headers['cache-control'] == 'private, no-store'
        assert download.headers['x-content-type-options'] == 'nosniff'
        assert (
            download.headers['content-disposition']
            == "attachment; filename*=UTF-8''notes.txt"
        )
        assert rejected_preview.status_code == 404

    def test_registered_image_preview_is_inline_and_private(
        self,
        mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
        postgres_database: PostgresDatabase,
    ) -> None:
        client, storage = mentor_attachment_client
        session_id, attempt_id, message_id = create_session(client)
        complete_response(postgres_database, session_id, attempt_id, message_id)
        batch_id = _create_attachment_batch(client, session_id)
        content = b'controlled image bytes'
        upload_key = str(uuid4())
        uploaded = client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': upload_key},
            files={'file': ('class photo.png', content, 'image/png')},
        )
        attachment_id = uploaded.json()['attachment_id']
        _mark_attachment_ready(postgres_database, attachment_id, image=True)
        submitted = client.post(
            f'/intelligence/mentor-sessions/{session_id}/messages',
            json={
                'submission_key': str(uuid4()),
                'content': 'Veja a imagem.',
                'attachment_batch_id': batch_id,
                'attachment_ids': [attachment_id],
            },
        )
        preview = client.get(
            f'/intelligence/mentor-sessions/{session_id}/attachments/{attachment_id}/file',
            params={'preview': 'true'},
        )

        assert uploaded.status_code == 201
        assert submitted.status_code == 202
        assert preview.status_code == 200
        assert preview.content == storage.objects[next(iter(storage.objects))][0]
        assert preview.headers['content-type'] == 'image/png'
        assert preview.headers['cache-control'] == 'private, no-store'
        assert preview.headers['x-content-type-options'] == 'nosniff'
        assert (
            preview.headers['content-disposition']
            == "inline; filename*=UTF-8''class%20photo.png"
        )

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Event
from time import monotonic, sleep
from typing import TYPE_CHECKING, NoReturn, Protocol, cast
from uuid import uuid4

import pytest
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shifu.intelligence.ai.agno.agents import MentorAttachmentVisionAgent
from shifu.intelligence.ai.agno.outputs import MentorAttachmentVisionOutput
from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.database.sqlalchemy.models import (
    MentorAttachmentChunkModel,
    MentorAttachmentModel,
)
from shifu.intelligence.providers.mentor_attachment.local_mentor_attachment_extractor_provider import (
    LocalMentorAttachmentExtractorProvider,
)
from shifu.shared.settings import get_settings
from tests.intelligence.server.agentos.mentor_attachment_test_support import (
    ATTACHMENT_TEXT,
    MODEL_ANSWER,
    create_goal,
    create_session,
    submit_message_with_attachment,
    upload_ready_text_attachment,
    wait_for_session_response,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from collections.abc import Generator

    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase
    from shifu.intelligence.core.domain.structures import MentorInferenceUsage


class _NamedTestNode(Protocol):
    name: str


pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)


@pytest.fixture(autouse=True)
def _set_pdf_render_budget_for_budget_case(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Generator[None]:
    test_node = cast('_NamedTestNode', request.node)
    settings_by_test = {
        'test_registered_pdf_render_byte_budget_keeps_page_uninterpreted': {
            'MENTOR_ATTACHMENT_MAX_PDF_RENDERED_BYTES': '1',
            'MENTOR_ATTACHMENT_MAX_PDF_PAGES': '2',
        },
        'test_registered_pdf_extraction_caps_page_text_output': {
            'MENTOR_ATTACHMENT_MAX_PDF_RENDERED_BYTES': '1',
        },
        'test_registered_upload_validation_rejects_malformed_parser_inputs': {
            'MENTOR_ATTACHMENT_MAX_IMAGE_PIXELS': '1',
        },
    }
    overrides = settings_by_test.get(test_node.name, {})
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)
    if overrides:
        get_settings.cache_clear()
    try:
        yield
    finally:
        if overrides:
            get_settings.cache_clear()


def test_registered_response_rejects_an_unauthorized_attachment_source(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_detail['response'])
    assert initial_snapshot['status'] == 'completed'

    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    agentos_fixture.model_transport.reject_attachment_source = True
    goal_id = create_goal(agentos_fixture.client)
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=goal_id,
    )

    detail = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id=attempt_id,
    )
    snapshot = cast('dict[str, object]', detail['response'])
    assert snapshot['status'] == 'failed'
    assert all(
        not cast('dict[str, object]', block)['sources']
        for block in cast('list[object]', snapshot['blocks'])
    )
    assert MODEL_ANSWER not in json.dumps(detail, ensure_ascii=False)
    assert ATTACHMENT_TEXT in json.dumps(
        agentos_fixture.model_transport.requests,
        ensure_ascii=False,
    )

    with postgres_database.engine.connect() as connection:
        process_run_count = connection.execute(
            text(
                'SELECT count(*) FROM '
                'agentos_intelligence.agentos_workflow_runs '
                'WHERE workflow_id = :workflow_id'
            ),
            {'workflow_id': 'intelligence-process-mentor-response'},
        ).scalar_one()

    assert process_run_count >= 1


def test_registered_text_extraction_caps_output_and_rejects_oversized_json(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']

    oversized_text = b'x' * 900_001 + b'TEXT_TAIL_SENTINEL'
    oversized_csv = ('x\n' * 100_001 + 'CSV_TAIL_SENTINEL\n').encode()
    oversized_json = json.dumps(
        {'text': 'x' * 200_001, 'tail': 'JSON_TAIL_SENTINEL'},
        separators=(',', ':'),
    ).encode()
    over_validation_limit_json = b'{"text":"' + b'x' * 1_000_001 + b'"}'
    uploads = (
        ('lesson.txt', 'text/plain', oversized_text),
        ('lesson.csv', 'text/csv', oversized_csv),
        ('lesson.json', 'application/json', oversized_json),
        ('large.json', 'application/json', over_validation_limit_json),
    )

    attachment_ids: list[str] = []
    for filename, media_type, content in uploads[:3]:
        upload_response = agentos_fixture.client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': (filename, content, media_type)},
        )
        assert upload_response.status_code == 201, upload_response.text
        attachment_ids.append(upload_response.json()['attachment_id'])

    filename, media_type, content = uploads[3]
    large_json_upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': (filename, content, media_type)},
    )
    assert large_json_upload_response.status_code == 422

    for index, attachment_id in enumerate(attachment_ids):
        deadline = monotonic() + 45
        attachment: dict[str, object] | None = None
        while monotonic() < deadline:
            response = agentos_fixture.client.get(
                f'/intelligence/mentor-attachment-batches/{batch_id}'
            )
            assert response.status_code == 200, response.text
            attachments = cast(
                'list[dict[str, object]]', response.json()['attachments']
            )
            attachment = next(
                item for item in attachments if item['attachment_id'] == attachment_id
            )
            if attachment['status'] in {'ready', 'partial', 'failed'}:
                break
            sleep(0.75)
        else:
            pytest.fail(f'Attachment extraction timed out: {attachment_id}')

        assert attachment is not None
        assert attachment['status'] == 'partial'
        expected_sentinel = (
            'TEXT_TAIL_SENTINEL',
            'CSV_TAIL_SENTINEL',
            'JSON_TAIL_SENTINEL',
        )[index]

        with postgres_database.engine.connect() as connection:
            chunk_summary = connection.execute(
                text(
                    'SELECT count(*), COALESCE(sum(char_length(content)), 0), '
                    'COALESCE(bool_or(position(:sentinel IN content) > 0), false) '
                    'FROM intelligence_mentor_attachment_chunks '
                    'WHERE attachment_id = :attachment_id'
                ),
                {
                    'sentinel': expected_sentinel or 'NO_SENTINEL_EXPECTED',
                    'attachment_id': attachment_id,
                },
            ).one()

        assert chunk_summary[0] > 0
        assert chunk_summary[1] <= 200_000
        assert not chunk_summary[2]


def test_registered_upload_validation_rejects_malformed_parser_inputs(
    agentos_fixture: RegisteredAgentOSFixture,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    jpeg_bytes = _image_bytes('JPEG')
    oversized_image = _image_bytes('PNG')
    invalid_uploads = (
        ('blank.txt', 'text/plain', b' \n\t'),
        ('invalid-encoding.txt', 'text/plain', b'\xff'),
        ('malformed.json', 'application/json', b'{not-json}'),
        ('malformed.csv', 'text/csv', b'"unterminated'),
        ('malformed.pdf', 'application/pdf', b'%PDF-1.4\nnot-a-pdf'),
        ('oversized-image.png', 'image/png', oversized_image),
        ('mismatched-image.png', 'image/png', jpeg_bytes),
        ('corrupt-image.webp', 'image/webp', b'not-an-image'),
    )

    for filename, media_type, content in invalid_uploads:
        response = agentos_fixture.client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': (filename, content, media_type)},
        )

        assert response.status_code == 422, (filename, response.text)


def test_registered_pdf_parse_outcomes_track_empty_encrypted_and_bad_pages(
    agentos_fixture: RegisteredAgentOSFixture,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']

    for filename, content in (
        ('empty.pdf', _empty_pdf()),
        ('encrypted.pdf', _encrypted_pdf()),
    ):
        response = agentos_fixture.client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': (filename, content, 'application/pdf')},
        )

        assert response.status_code == 422, (filename, response.text)

    page_error_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={
            'file': (
                'one-unreadable-page.pdf',
                _pdf_with_page_error(),
                'application/pdf',
            )
        },
    )
    assert page_error_response.status_code == 201, page_error_response.text
    attachment_id = page_error_response.json()['attachment_id']

    deadline = monotonic() + 45
    attachment: dict[str, object] | None = None
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachments = cast('list[dict[str, object]]', response.json()['attachments'])
        attachment = next(
            item for item in attachments if item['attachment_id'] == attachment_id
        )
        if attachment['status'] in {'ready', 'partial', 'failed'}:
            break
        sleep(0.75)
    else:
        pytest.fail(f'PDF page-error extraction timed out: {attachment_id}')

    assert attachment is not None
    assert attachment['status'] == 'partial'
    assert attachment['analyzed_pages'] == [1]
    assert attachment['illegible_pages'] == [2]
    assert attachment['uninterpreted_pages'] == []


def test_registered_raster_extraction_parses_image_and_pdf_pages(
    agentos_fixture: RegisteredAgentOSFixture,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    raster_uploads = (
        ('lesson.png', 'image/png', _image_bytes('PNG')),
        ('lesson.jpg', 'image/jpeg', _image_bytes('JPEG')),
        ('lesson.webp', 'image/webp', _image_bytes('WEBP')),
    )
    image_attachment_ids: list[str] = []
    for filename, media_type, content in raster_uploads:
        upload_response = agentos_fixture.client.post(
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': (filename, content, media_type)},
        )
        assert upload_response.status_code == 201, upload_response.text
        image_attachment_ids.append(upload_response.json()['attachment_id'])

    pdf_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('scanned.pdf', _pdf_with_text_pages(''), 'application/pdf')},
    )
    assert pdf_response.status_code == 201, pdf_response.text
    pdf_attachment_id = pdf_response.json()['attachment_id']
    expected_attachment_ids = {*image_attachment_ids, pdf_attachment_id}

    deadline = monotonic() + 45
    attachments_by_id: dict[str, dict[str, object]] = {}
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachments = cast('list[dict[str, object]]', response.json()['attachments'])
        attachments_by_id = {
            str(item['attachment_id']): item
            for item in attachments
            if item['attachment_id'] in expected_attachment_ids
        }
        if len(attachments_by_id) == len(expected_attachment_ids) and all(
            item['status'] in {'ready', 'partial', 'failed'}
            for item in attachments_by_id.values()
        ):
            break
        sleep(0.75)
    else:
        pytest.fail(f'Raster extraction timed out: {expected_attachment_ids}')

    for image_attachment_id in image_attachment_ids:
        image_attachment = attachments_by_id[image_attachment_id]
        assert image_attachment['status'] == 'ready'
        assert image_attachment['analyzed_pages'] == [1]
        assert image_attachment['illegible_pages'] == []
        assert image_attachment['uninterpreted_pages'] == []
    pdf_attachment = attachments_by_id[pdf_attachment_id]
    assert pdf_attachment['status'] == 'ready'
    assert pdf_attachment['analyzed_pages'] == [1]
    assert pdf_attachment['illegible_pages'] == []
    assert pdf_attachment['uninterpreted_pages'] == []
    assert 'vision' in agentos_fixture.model_transport.model_profiles


def test_registered_visual_extraction_marks_an_unreadable_page_without_vision_text(
    agentos_fixture: RegisteredAgentOSFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def return_unreadable(
        *_args: object, **_kwargs: object
    ) -> MentorAttachmentVisionOutput:
        return MentorAttachmentVisionOutput(legible=False, description='')

    monkeypatch.setattr(
        MentorAttachmentVisionAgent,
        'analyze',
        cast('Callable[..., MentorAttachmentVisionOutput]', return_unreadable),
    )

    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={
            'file': ('unreadable.png', _image_bytes('PNG'), 'image/png'),
        },
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    attachment: dict[str, object] | None = None
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachments = cast('list[dict[str, object]]', response.json()['attachments'])
        attachment = next(
            item for item in attachments if item['attachment_id'] == attachment_id
        )
        if attachment['status'] in {'ready', 'partial', 'failed'}:
            break
        sleep(0.75)
    else:
        pytest.fail(f'Visual extraction timed out: {attachment_id}')

    assert attachment is not None
    assert attachment['status'] == 'failed'
    assert attachment['analyzed_pages'] == []
    assert attachment['illegible_pages'] == [1]
    assert attachment['uninterpreted_pages'] == []


def test_registered_extraction_marks_invalid_text_as_invalid_file(
    agentos_fixture: RegisteredAgentOSFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_extraction(
        _provider: LocalMentorAttachmentExtractorProvider,
        _content: bytes,
        _media_type: str,
        _attachment_id: str,
        _generation: int,
    ) -> NoReturn:
        raise MentorAttachmentInvalidError

    monkeypatch.setattr(
        LocalMentorAttachmentExtractorProvider,
        'extract',
        reject_extraction,
    )
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('lesson.txt', b'lesson text', 'text/plain')},
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    attachment: dict[str, object] | None = None
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachments = cast('list[dict[str, object]]', response.json()['attachments'])
        attachment = next(
            item for item in attachments if item['attachment_id'] == attachment_id
        )
        if attachment['status'] in {'ready', 'partial', 'failed'}:
            break
        sleep(0.75)
    else:
        pytest.fail(f'Invalid text extraction timed out: {attachment_id}')

    assert attachment is not None
    assert attachment['status'] == 'failed'
    assert attachment['failure_code'] == 'invalid_file'
    assert attachment['analyzed_pages'] == []
    assert attachment['illegible_pages'] == []


def test_registered_extraction_releases_claim_when_provider_fails(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_extraction(
        _provider: LocalMentorAttachmentExtractorProvider,
        _content: bytes,
        _media_type: str,
        _attachment_id: str,
        _generation: int,
    ) -> NoReturn:
        raise RuntimeError('controlled transient extraction failure')

    monkeypatch.setattr(
        LocalMentorAttachmentExtractorProvider,
        'extract',
        fail_extraction,
    )
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={
            'file': (
                'lesson.txt',
                b'valid input before transient failure',
                'text/plain',
            )
        },
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    claim_released = False
    while monotonic() < deadline:
        with Session(postgres_database.engine) as session:
            attachment = session.get(MentorAttachmentModel, attachment_id)
            if (
                attachment is not None
                and attachment.status == 'processing'
                and attachment.execution_owner is None
            ):
                claim_released = True
                break
        sleep(0.25)
    assert claim_released, f'Prepare workflow did not release {attachment_id}'

    with Session(postgres_database.engine) as session:
        attachment = session.get(MentorAttachmentModel, attachment_id)
    assert attachment is not None
    assert attachment.status == 'processing'
    assert attachment.execution_owner is None


def test_registered_text_extraction_persists_local_chunks(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    extracted_text = 'The registered local extractor preserves this lesson text.'
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('lesson.txt', extracted_text.encode(), 'text/plain')},
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    attachment: dict[str, object] | None = None
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachments = cast('list[dict[str, object]]', response.json()['attachments'])
        attachment = next(
            item for item in attachments if item['attachment_id'] == attachment_id
        )
        if attachment['status'] in {'ready', 'partial', 'failed'}:
            break
        sleep(0.75)
    else:
        pytest.fail(f'Text extraction timed out: {attachment_id}')

    assert attachment is not None
    assert attachment['status'] == 'ready'
    assert attachment['failure_code'] is None
    with Session(postgres_database.engine) as session:
        chunks = session.scalars(
            select(MentorAttachmentChunkModel).where(
                MentorAttachmentChunkModel.attachment_id == attachment_id
            )
        ).all()

    assert len(chunks) == 1
    assert chunks[0].content == extracted_text
    assert chunks[0].page_number is None
    assert chunks[0].locator.startswith('chars:')
    assert agentos_fixture.model_transport.requests == []


def test_registered_pdf_extraction_caps_page_text_output(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    content = _pdf_with_split_text_page(
        'x' * 200_001,
        'PDF_TAIL_SENTINEL',
        'Beyond page text budget',
    )
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('lesson.pdf', content, 'application/pdf')},
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachment = cast('dict[str, object]', response.json()['attachments'][0])
        if attachment['status'] in {'ready', 'partial', 'failed'}:
            break
        sleep(0.75)
    else:
        pytest.fail(f'PDF extraction timed out: {attachment_id}')

    assert attachment['status'] == 'partial'
    assert attachment['analyzed_pages'] == [1]
    assert attachment['uninterpreted_pages'] == [2]
    with postgres_database.engine.connect() as connection:
        chunk_summary = connection.execute(
            text(
                'SELECT count(*), COALESCE(sum(char_length(content)), 0), '
                'COALESCE(bool_or(position(:sentinel IN content) > 0), false) '
                'FROM intelligence_mentor_attachment_chunks '
                'WHERE attachment_id = :attachment_id'
            ),
            {
                'sentinel': 'PDF_TAIL_SENTINEL',
                'attachment_id': attachment_id,
            },
        ).one()

    assert chunk_summary[0] > 0
    assert chunk_summary[1] <= 200_000
    assert not chunk_summary[2]


def test_registered_pdf_render_byte_budget_keeps_page_uninterpreted(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']
    content = _pdf_with_text_pages('Readable page', '', 'Beyond page limit')
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('scanned.pdf', content, 'application/pdf')},
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    attachment: dict[str, object] | None = None
    while monotonic() < deadline:
        response = agentos_fixture.client.get(
            f'/intelligence/mentor-attachment-batches/{batch_id}'
        )
        assert response.status_code == 200, response.text
        attachment = cast('dict[str, object]', response.json()['attachments'][0])
        if attachment['status'] in {'ready', 'partial', 'failed'}:
            break
        sleep(0.75)
    else:
        pytest.fail(f'PDF render budget processing timed out: {attachment_id}')

    assert attachment is not None
    assert attachment['status'] == 'partial'
    assert attachment['analyzed_pages'] == [1]
    assert attachment['uninterpreted_pages'] == [2, 3]
    with postgres_database.engine.connect() as connection:
        chunk_count = connection.execute(
            text(
                'SELECT count(*) FROM intelligence_mentor_attachment_chunks '
                'WHERE attachment_id = :attachment_id'
            ),
            {'attachment_id': attachment_id},
        ).scalar_one()
    assert chunk_count > 0


def _pdf_with_split_text_page(
    first_text: str, second_text: str, *later_page_texts: str
) -> bytes:
    replacement = b') Tj ET BT /F1 12 Tf 72 720 Td ('
    marker = b'_' * len(replacement)
    content = _pdf_with_text_pages(
        f'{first_text}{marker.decode()}{second_text}', *later_page_texts
    )
    assert content.count(marker) == 1
    return content.replace(marker, replacement, 1)


def _empty_pdf() -> bytes:
    output = BytesIO()
    PdfWriter().write(output)
    return output.getvalue()


def _encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt('parser-test-password')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _pdf_with_page_error() -> bytes:
    content = _pdf_with_text_pages('Readable page', 'x' * 10_000)
    lengths = list(re.finditer(rb'/Length (\d+) >>', content))
    assert len(lengths) == 2
    length = lengths[1]
    assert len(length.group(1)) == len(b'0 0 R')
    return content[: length.start(1)] + b'0 0 R' + content[length.end(1) :]


def _pdf_with_text_pages(*page_texts: str) -> bytes:
    page_object_numbers = (3, *(6 + 2 * index for index in range(len(page_texts) - 1)))
    stream_object_numbers = (
        5,
        *(7 + 2 * index for index in range(len(page_texts) - 1)),
    )
    kids = ' '.join(f'{number} 0 R' for number in page_object_numbers)
    streams = tuple(
        f'BT /F1 12 Tf 72 720 Td ({text}) Tj ET'.encode('ascii') for text in page_texts
    )
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        f'<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>'.encode('ascii'),
        (
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            '/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>'
        ).encode('ascii'),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        _pdf_text_stream_object(streams[0]),
    ]
    for page_index in range(1, len(page_texts)):
        stream_object_number = stream_object_numbers[page_index]
        objects.extend(
            (
                (
                    f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
                    f'/Resources << /Font << /F1 4 0 R >> >> '
                    f'/Contents {stream_object_number} 0 R >>'
                ).encode('ascii'),
                _pdf_text_stream_object(streams[page_index]),
            )
        )

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for object_number, object_content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{object_number} 0 obj\n'.encode('ascii'))
        pdf.extend(object_content)
        pdf.extend(b'\nendobj\n')

    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(offsets)}\n'.encode('ascii'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
    pdf.extend(
        f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n'.encode('ascii')
        + str(xref_offset).encode('ascii')
        + b'\n%%EOF\n'
    )
    return bytes(pdf)


def _pdf_text_stream_object(stream: bytes) -> bytes:
    return (
        b'<< /Length '
        + str(len(stream)).encode('ascii')
        + b' >>\nstream\n'
        + stream
        + b'\nendstream'
    )


def _image_bytes(image_format: str) -> bytes:
    image = Image.new('RGB', (2, 2), color=(40, 90, 160))
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    image.close()
    return buffer.getvalue()


class TestPrepareMentorAttachmentWorkflow:
    def test_registered_vision_keeps_api_responsive_and_runs_once(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        entered = Event()
        release = Event()
        analyze = MentorAttachmentVisionAgent.analyze
        vision_calls: list[str] = []

        def held_analysis(
            agent: MentorAttachmentVisionAgent,
            image_content: bytes,
            *,
            media_type: str,
            attachment_id: str,
            page_number: int,
            usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
        ) -> MentorAttachmentVisionOutput:
            vision_calls.append(attachment_id)
            entered.set()
            assert release.wait(30), 'Controlled vision request was never released'
            return analyze(
                agent,
                image_content,
                media_type=media_type,
                attachment_id=attachment_id,
                page_number=page_number,
                usage_recorder=usage_recorder,
            )

        monkeypatch.setattr(MentorAttachmentVisionAgent, 'analyze', held_analysis)
        client = agentos_fixture.client
        batch_response = client.post('/intelligence/mentor-attachment-batches', json={})
        assert batch_response.status_code == 201, batch_response.text
        batch_id = batch_response.json()['batch_id']
        batch_path = f'/intelligence/mentor-attachment-batches/{batch_id}'

        with ThreadPoolExecutor(max_workers=2) as requests:
            upload = requests.submit(
                client.post,
                f'{batch_path}/attachments',
                data={'upload_key': str(uuid4())},
                files={'file': ('synthetic.png', _image_bytes('PNG'), 'image/png')},
            )
            try:
                assert entered.wait(15), 'Registered vision extraction did not start'
                health = requests.submit(client.get, '/health').result(timeout=2)
                assert health.status_code == 200, health.text
                batch = requests.submit(client.get, batch_path).result(timeout=2)
                assert batch.status_code == 200, batch.text
                assert batch.json()['attachments'][0]['status'] == 'processing'
            finally:
                release.set()
            upload_response = upload.result(timeout=10)

        assert upload_response.status_code == 201, upload_response.text
        attachment_id = upload_response.json()['attachment_id']
        deadline = monotonic() + 20
        while monotonic() < deadline:
            with Session(postgres_database.engine) as session:
                attachment = session.get(MentorAttachmentModel, attachment_id)
                if attachment is not None and attachment.status == 'ready':
                    assert attachment.analyzed_pages == [1]
                    assert attachment.execution_owner is None
                    chunks = session.scalars(
                        select(MentorAttachmentChunkModel).where(
                            MentorAttachmentChunkModel.attachment_id == attachment_id
                        )
                    ).all()
                    assert len(chunks) == 1
                    break
            sleep(0.1)
        else:
            pytest.fail('Registered vision extraction did not commit its result')

        assert vision_calls == [attachment_id]
        assert len(agentos_fixture.model_transport.requests) == 1

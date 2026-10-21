from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Event
from time import monotonic, sleep
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from shifu.intelligence.ai.agno.agents import MentorAttachmentVisionAgent
from shifu.intelligence.ai.agno.workflows.prepare_mentor_attachment_workflow import (
    PrepareMentorAttachmentWorkflow,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.pipes import IntelligencePipe
from tests.intelligence.server.agentos.mentor_attachment_test_support import (
    ATTACHMENT_TEXT,
    create_session,
    upload_ready_text_attachment,
)

if TYPE_CHECKING:
    from agno.workflow.types import StepInput, StepOutput

    from collections.abc import Callable

    from shifu.intelligence.ai.agno.outputs import MentorAttachmentVisionOutput
    from shifu.intelligence.core.domain.structures import MentorInferenceUsage
    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)


def test_registered_attachment_workflow_reloads_source_after_context_loss(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_extract = PrepareMentorAttachmentWorkflow._extract  # noqa: SLF001  # pyright: ignore[reportPrivateUsage] - context-loss simulation targets the registered step boundary.
    simulated_context_loss = False

    def extract_then_clear_context(
        workflow: PrepareMentorAttachmentWorkflow, step_input: StepInput
    ) -> StepOutput:
        nonlocal simulated_context_loss
        output = original_extract(workflow, step_input)
        if not simulated_context_loss and output.content != 'no_op':
            workflow._execution.set(None)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage] - clear process-local state to simulate context loss.
            simulated_context_loss = True
        return output

    monkeypatch.setattr(
        PrepareMentorAttachmentWorkflow, '_extract', extract_then_clear_context
    )

    session_id = create_session(agentos_fixture.client)
    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )

    assert simulated_context_loss
    with postgres_database.engine.connect() as connection:
        run_data = connection.execute(
            text(
                'SELECT status, run_data::text FROM agentos_intelligence.agentos_workflow_runs '
                'WHERE workflow_id = :workflow_id'
            ),
            {'workflow_id': 'intelligence-prepare-mentor-attachment'},
        ).all()

    assert run_data
    assert any(str(status).lower() == 'completed' for status, _data in run_data)
    assert all(ATTACHMENT_TEXT not in data for _status, data in run_data)

    database = IntelligencePipe.create_database(postgres_database.engine)
    with database.transaction() as repositories:
        attachment = repositories.mentor_attachments.find_by_id(attachment_id)
        assert attachment is not None
        assert attachment.batch_id == batch_id
        assert attachment.status is MentorAttachmentStatus.READY
        chunks = repositories.mentor_attachment_chunks.find_by_attachment_id(
            attachment_id, attachment.generation
        )

    assert chunks


def test_registered_attachment_cleanup_removes_storage_and_chunks(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    assert len(agentos_fixture.storage.objects) == 1

    removed = agentos_fixture.client.delete(
        f'/intelligence/mentor-sessions/{session_id}'
    )
    assert removed.status_code == 204, removed.text

    database = IntelligencePipe.create_database(postgres_database.engine)
    deadline = monotonic() + 30
    cleaned = False
    while monotonic() < deadline:
        with database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
            assert attachment is not None
            assert attachment.batch_id == batch_id
            chunks = repositories.mentor_attachment_chunks.find_by_attachment_id(
                attachment_id, attachment.generation
            )
            cleaned = (
                attachment.status is MentorAttachmentStatus.REMOVED
                and not chunks
                and not agentos_fixture.storage.objects
            )
        if cleaned:
            break
        sleep(0.25)

    assert cleaned, 'registered purge workflow did not remove stored attachment data'


def test_registered_attachment_removal_cleans_storage_and_chunks_by_batch(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    _session_id = create_session(agentos_fixture.client)
    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=_session_id,
    )
    assert len(agentos_fixture.storage.objects) == 1

    removed = agentos_fixture.client.delete(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}'
    )
    assert removed.status_code == 204, removed.text

    database = IntelligencePipe.create_database(postgres_database.engine)
    deadline = monotonic() + 30
    cleaned = False
    while monotonic() < deadline:
        with database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
            assert attachment is not None
            chunks = repositories.mentor_attachment_chunks.find_by_attachment_id(
                attachment_id, attachment.generation
            )
            cleaned = (
                attachment.batch_id == batch_id
                and attachment.status is MentorAttachmentStatus.REMOVED
                and not chunks
                and not agentos_fixture.storage.objects
            )
        if cleaned:
            break
        sleep(0.25)

    assert cleaned, 'registered batch purge did not remove stored attachment data'


def test_registered_attachment_removal_during_vision_inference_does_not_resurrect_data(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_analyze = MentorAttachmentVisionAgent.analyze
    inference_started = Event()
    release_inference = Event()

    def analyze_then_wait(
        agent: MentorAttachmentVisionAgent,
        image_content: bytes,
        *,
        media_type: str,
        attachment_id: str,
        page_number: int,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
    ) -> MentorAttachmentVisionOutput:
        inference_started.set()
        if not release_inference.wait(timeout=30):
            raise TimeoutError('test did not release blocked vision inference')
        return original_analyze(
            agent,
            image_content,
            media_type=media_type,
            attachment_id=attachment_id,
            page_number=page_number,
            usage_recorder=usage_recorder,
        )

    monkeypatch.setattr(MentorAttachmentVisionAgent, 'analyze', analyze_then_wait)

    session_id = create_session(agentos_fixture.client)
    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches', json={'session_id': session_id}
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']

    concurrent_client = TestClient(
        agentos_fixture.client.app, headers=dict(agentos_fixture.client.headers)
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        upload = executor.submit(
            agentos_fixture.client.post,
            f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
            data={'upload_key': str(uuid4())},
            files={
                'file': (
                    'lesson.png',
                    _small_png(),
                    'image/png',
                )
            },
        )
        try:
            assert inference_started.wait(timeout=30), (
                'registered preparation workflow did not reach vision inference'
            )
            batch = concurrent_client.get(
                f'/intelligence/mentor-attachment-batches/{batch_id}'
            )
            assert batch.status_code == 200, batch.text
            attachment_id = batch.json()['attachments'][0]['attachment_id']

            removed = concurrent_client.delete(
                f'/intelligence/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}'
            )
            assert removed.status_code == 204, removed.text
        finally:
            release_inference.set()

        uploaded = upload.result(timeout=45)
        assert uploaded.status_code == 201, uploaded.text
    concurrent_client.close()

    database = IntelligencePipe.create_database(postgres_database.engine)
    deadline = monotonic() + 30
    cleaned = False
    while monotonic() < deadline:
        with database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
            assert attachment is not None
            chunks = repositories.mentor_attachment_chunks.find_by_attachment_id(
                attachment_id, attachment.generation
            )
            cleaned = (
                attachment.status is MentorAttachmentStatus.REMOVED
                and not chunks
                and not agentos_fixture.storage.objects
            )
        if cleaned:
            break
        sleep(0.25)

    assert cleaned, 'late inference result resurrected removed attachment data'


def _small_png() -> bytes:
    image = Image.new('RGB', (2, 2), color=(40, 90, 160))
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    image.close()
    return buffer.getvalue()

"""The attachment preparation workflow run in process over the disposable
PostgreSQL: real use cases, the uploaded file in a stubbed object store, a mocked
extractor and a mocked vision agent."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock
from uuid import uuid4

import pytest

from shifu.intelligence.ai.agno.agents import MentorAttachmentVisionAgent
from shifu.intelligence.ai.agno.outputs import MentorAttachmentVisionOutput
from shifu.intelligence.ai.agno.workflows import AgnoPrepareMentorAttachmentWorkflow
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentExtraction,
    MentorInferenceUsage,
)
from shifu.intelligence.core.interfaces import MentorAttachmentExtractorProvider
from shifu.intelligence.core.use_cases import (
    CompleteMentorAttachmentUseCase,
    FailMentorAttachmentUseCase,
    PrepareMentorAttachmentUseCase,
    ReleaseMentorAttachmentClaimUseCase,
    RenewMentorAttachmentClaimUseCase,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.intelligence_fixture import (
        IntelligenceFixture,
        MentorAttachmentStorageStub,
    )
    from collections.abc import Callable

    from fastapi.testclient import TestClient

    from shifu.intelligence.core.domain.entities import MentorAttachment

PNG = b'\x89PNG\r\n\x1a\n' + bytes(range(256)) * 4
DESCRIPTION = 'A página mostra que 1/2 é equivalente a 2/4.'


def grant(account_id: str, operation_key: str) -> MentorAccessGrant:
    return MentorAccessGrant(
        account_id=account_id,
        access_revision='controlled-test-revision',
        operation_key=operation_key,
    )


def vision(*, legible: bool) -> Callable[..., MentorAttachmentVisionOutput]:
    """The mocked vision agent: it reports its usage like the real one."""

    def analyze(
        _image: bytes,
        *,
        media_type: str,
        attachment_id: str,
        page_number: int,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
    ) -> MentorAttachmentVisionOutput:
        del media_type
        if usage_recorder is not None:
            usage_recorder(
                MentorInferenceUsage(
                    call_key=f'vision:{attachment_id}:{page_number}',
                    profile='mentor-attachment-vision',
                    used_tokens=40,
                )
            )
        return MentorAttachmentVisionOutput(
            legible=legible, description=DESCRIPTION if legible else ''
        )

    return analyze


class Harness:
    def __init__(
        self,
        fixture: IntelligenceFixture,
        client: TestClient,
        storage: MentorAttachmentStorageStub,
    ) -> None:
        self.fixture = fixture
        self.client = client
        self.usage: list[MentorInferenceUsage] = []
        database = fixture.database
        clock = SystemClockProvider()
        access = Mock(spec=MentorAccessProvider)
        access.authorize.side_effect = grant
        self.extractor = Mock(spec=MentorAttachmentExtractorProvider)
        self.extractor.extract.return_value = MentorAttachmentExtraction(
            chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=(1,)
        )
        self.extractor.render_visual_pages.return_value = ((1, b'rendered-page'),)
        self.vision_agent = Mock(spec=MentorAttachmentVisionAgent)
        self.vision_agent.analyze.side_effect = vision(legible=True)
        # The workflow runs on a per-call clone and copies its agent; keep the mock.
        self.vision_agent.deep_copy.return_value = self.vision_agent
        self.workflow = AgnoPrepareMentorAttachmentWorkflow(
            PrepareMentorAttachmentUseCase(database, clock, access, storage),
            CompleteMentorAttachmentUseCase(database, clock, access),
            FailMentorAttachmentUseCase(database, clock, access),
            RenewMentorAttachmentClaimUseCase(database, clock, access),
            ReleaseMentorAttachmentClaimUseCase(database),
            self.extractor,
            self.vision_agent,
            SystemIdentifierProvider(),
            max_pdf_pages=3,
            usage_recorder=self.usage.append,
        )

    def upload_image(self) -> str:
        """A session, a batch and one uploaded PNG; returns the attachment id."""
        session_id, _, _ = self.fixture.create_session(self.client)
        batch = self.client.post(
            '/intelligence/mentor-attachment-batches', json={'session_id': session_id}
        )
        assert batch.status_code == 201
        upload = self.client.post(
            f'/intelligence/mentor-attachment-batches/{batch.json()["batch_id"]}/attachments',
            data={'upload_key': str(uuid4())},
            files={'file': ('page.png', PNG, 'image/png')},
        )
        assert upload.status_code == 201, upload.text
        return str(upload.json()['attachment_id'])

    def run(self, attachment_id: str) -> object:
        return self.workflow.run(
            input=json.dumps({'attachment_id': attachment_id, 'generation': 1})
        ).content

    def attachment(self, attachment_id: str) -> MentorAttachment:
        with self.fixture.database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
        assert attachment is not None
        return attachment

    def chunks(self, attachment_id: str) -> tuple[tuple[str, str], ...]:
        with self.fixture.database.transaction() as repositories:
            chunks = repositories.mentor_attachment_chunks.find_by_attachment_id(
                attachment_id, 1
            )
        return tuple((chunk.locator, chunk.content) for chunk in chunks)


@pytest.fixture
def harness(
    intelligence_fixture: IntelligenceFixture,
    mentor_attachment_client: tuple[TestClient, MentorAttachmentStorageStub],
) -> Harness:
    client, storage = mentor_attachment_client
    return Harness(intelligence_fixture, client, storage)


class TestAgnoPrepareMentorAttachmentWorkflow:
    def test_makes_a_legible_image_ready_with_its_vision_chunk(
        self, harness: Harness
    ) -> None:
        attachment_id = harness.upload_image()

        output = harness.run(attachment_id)

        assert output == json.dumps(
            {'attachment_id': attachment_id, 'status': 'ready'}, separators=(',', ':')
        )
        attachment = harness.attachment(attachment_id)
        assert attachment.status is MentorAttachmentStatus.READY
        assert attachment.analyzed_pages == (1,)
        assert attachment.execution_owner is None
        assert harness.chunks(attachment_id) == (('page:1/vision', DESCRIPTION),)
        assert [usage.call_key for usage in harness.usage] == [
            f'vision:{attachment_id}:1'
        ]

    def test_fails_an_illegible_image_as_unreadable(self, harness: Harness) -> None:
        harness.vision_agent.analyze.side_effect = vision(legible=False)
        attachment_id = harness.upload_image()

        harness.run(attachment_id)

        attachment = harness.attachment(attachment_id)
        assert attachment.status is MentorAttachmentStatus.FAILED
        assert attachment.failure_code == 'unreadable_file'
        assert attachment.illegible_pages == (1,)
        assert harness.chunks(attachment_id) == ()

    def test_fails_an_invalid_file_without_calling_the_vision_agent(
        self, harness: Harness
    ) -> None:
        harness.extractor.extract.side_effect = MentorAttachmentInvalidError
        attachment_id = harness.upload_image()

        harness.run(attachment_id)

        attachment = harness.attachment(attachment_id)
        assert attachment.status is MentorAttachmentStatus.FAILED
        assert attachment.failure_code == 'invalid_file'
        harness.vision_agent.analyze.assert_not_called()

    def test_releases_the_claim_and_raises_when_the_vision_agent_fails(
        self, harness: Harness
    ) -> None:
        harness.vision_agent.analyze.side_effect = RuntimeError('vision endpoint down')
        attachment_id = harness.upload_image()

        # Agno records the failed step; the claim is released before it does.
        harness.run(attachment_id)

        attachment = harness.attachment(attachment_id)
        assert attachment.status is not MentorAttachmentStatus.READY
        assert attachment.execution_owner is None
        assert harness.chunks(attachment_id) == ()

    def test_does_nothing_on_a_second_run_of_a_ready_attachment(
        self, harness: Harness
    ) -> None:
        attachment_id = harness.upload_image()
        harness.run(attachment_id)

        assert harness.run(attachment_id) == 'no_op'

        assert harness.vision_agent.analyze.call_count == 1
        assert harness.attachment(attachment_id).status is MentorAttachmentStatus.READY

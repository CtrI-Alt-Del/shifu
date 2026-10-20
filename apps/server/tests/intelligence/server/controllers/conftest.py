from __future__ import annotations

from collections.abc import Generator
from unittest.mock import Mock, create_autospec
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.core.domain.structures import MentorAccessGrant

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.core.domain.structures import MentorAttachmentExtraction
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import FileStoragePipe
from shifu.shared.pipes import SharedPipe
from shifu.shared.messaging.inngest.inngest_broker import InngestBroker
from shifu.shared.messaging.agentos.agentos_broker import AgentOSBroker

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from tests.fixtures.postgres_fixture import PostgresDatabase


MENTOR_ACCOUNT = AuthenticatedUser(
    account_id='01JACCOUNT000000000000TEST',
    display_name='Learner Test',
    time_zone=None,
)


class MentorTitleWorkflowStub:
    def generate(self, first_message: str) -> str:
        del first_message
        return 'Conversa de teste'


class MentorAttachmentStorageStub:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, object_key: str, content: bytes, media_type: str) -> None:
        self.objects[object_key] = (content, media_type)

    def read(self, object_key: str) -> bytes:
        return self.objects[object_key][0]

    def remove(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class MentorAttachmentExtractorStub:
    def validate(self, content: bytes, media_type: str) -> None:
        del content, media_type

    def extract(
        self, content: bytes, media_type: str, attachment_id: str, generation: int
    ) -> MentorAttachmentExtraction:
        del content, media_type, attachment_id, generation
        return MentorAttachmentExtraction(
            chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
        )

    def render_visual_pages(
        self, content: bytes, media_type: str, page_numbers: tuple[int, ...]
    ) -> tuple[tuple[int, bytes], ...]:
        del content, media_type, page_numbers
        return ()


@pytest.fixture(autouse=True)
def isolate_mentor_outbox_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    # HTTP tests assert real transactional outbox rows. Delivery is exercised by
    # disposable registered-job tests, never the shared development server.
    monkeypatch.setattr('shifu.app.InngestBroker', create_autospec(InngestBroker))


@pytest.fixture
def mentor_client(
    postgres_database: PostgresDatabase,
) -> Generator[TestClient]:
    app: FastAPI = FastAPIApp.register(postgres_database.engine)
    configure_mentor_access(app)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: MENTOR_ACCOUNT
    app.dependency_overrides[IntelligencePipe.get_generate_mentor_title_workflow] = (
        MentorTitleWorkflowStub
    )
    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client


@pytest.fixture
def mentor_attachment_client(
    postgres_database: PostgresDatabase,
) -> Generator[tuple[TestClient, MentorAttachmentStorageStub]]:
    app: FastAPI = FastAPIApp.register(postgres_database.engine)
    configure_mentor_access(app)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: MENTOR_ACCOUNT
    app.dependency_overrides[IntelligencePipe.get_generate_mentor_title_workflow] = (
        MentorTitleWorkflowStub
    )
    storage = MentorAttachmentStorageStub()
    extractor = MentorAttachmentExtractorStub()
    app.dependency_overrides[FileStoragePipe.get_file_storage_provider] = lambda: (
        storage
    )
    app.dependency_overrides[
        IntelligencePipe.get_mentor_attachment_extractor_provider
    ] = lambda: extractor

    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client, storage


def configure_mentor_access(app: FastAPI) -> Mock:
    access = create_autospec(MentorAccessProvider, instance=True)

    def grant(account_id: str, operation_key: str) -> MentorAccessGrant:
        return MentorAccessGrant(
            account_id=account_id,
            access_revision='controlled-test-revision',
            operation_key=operation_key,
        )

    access.authorize.side_effect = grant
    app.dependency_overrides[IntelligencePipe.get_mentor_access_provider] = lambda: (
        access
    )
    return access


@pytest.fixture
def planning_client(
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient]:
    # Planning HTTP tests assert the outbox rows themselves; the AgentOS relay only
    # runs in the registered-workflow tests.
    monkeypatch.setattr(
        'shifu.shared.messaging.agentos.agentos_runtime.AgentOSBroker',
        create_autospec(AgentOSBroker),
    )
    app: FastAPI = FastAPIApp.register(postgres_database.engine)
    configure_mentor_access(app)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: MENTOR_ACCOUNT
    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client

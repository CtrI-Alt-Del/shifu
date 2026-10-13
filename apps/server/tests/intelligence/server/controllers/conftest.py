from __future__ import annotations
from unittest.mock import Mock, create_autospec
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.core.domain.structures import MentorAccessGrant

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from shifu.shared.messaging.inngest.inngest_broker import InngestBroker

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

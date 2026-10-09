from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe

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


@pytest.fixture
def mentor_client(
    postgres_database: PostgresDatabase,
) -> Generator[TestClient]:
    app: FastAPI = FastAPIApp.register(postgres_database.engine)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: MENTOR_ACCOUNT
    app.dependency_overrides[IntelligencePipe.get_generate_mentor_title_workflow] = (
        MentorTitleWorkflowStub
    )
    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client

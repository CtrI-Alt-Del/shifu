from collections.abc import Iterator
from uuid import uuid4
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures.diagnostic_overview import DiagnosticOverview
import shifu.learning.rest.controllers.get_diagnostic_controller as diagnostic_controller

_AUTHORIZATION = {'Authorization': 'Bearer test-access-token'}


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    app = FastAPIApp.register(postgres_database.engine)
    app.state.authentication_provider = _Authentication()
    app.state.inngest_broker = _NoopBroker()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


def _post(
    client: TestClient,
    path: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
) -> Response:
    return cast(
        'Response',
        client.post(path, headers=headers, json=payload),  # pyright: ignore[reportUnknownMemberType]
    )


def _get(
    client: TestClient, path: str, headers: dict[str, str] | None = None
) -> Response:
    return cast(
        'Response',
        client.get(path, headers=headers),  # pyright: ignore[reportUnknownMemberType]
    )


def _create_goal(client: TestClient) -> str:
    response = _post(
        client,
        '/learning/goals',
        _AUTHORIZATION,
        {
            'title': 'Aprender decisões',
            'description': 'Praticar decisões com evidência por Conceito.',
            'skillIds': [SEED_ADAPTIVE_SKILL_ID],
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()['goalId'])


class TestGetDiagnosticController:
    def test_settled_response_exposes_initial_gap_without_a_recommendation(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class _NoFallbackUseCase:
            def __init__(self, *args: object) -> None:
                pass

            def execute(
                self,
                account_id: str,
                goal_id: str,
                skill_id: str,
                diagnostic_run_id: str | None = None,
            ) -> DiagnosticOverview:
                return DiagnosticOverview(
                    status=SkillExperienceStatus.LEARNING,
                    run_state='settled',
                    initial_recommendation_gap=('curriculum_or_assessment_unavailable'),
                )

        monkeypatch.setattr(
            diagnostic_controller, 'GetDiagnosticUseCase', _NoFallbackUseCase
        )
        response = _get(
            client,
            f'/learning/goals/01ARZ3NDEKTSV4RRFFQ69G5FAV/skills/{SEED_ADAPTIVE_SKILL_ID}/diagnostic',
            _AUTHORIZATION,
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['initialRecommendation'] is None
        assert body['initialRecommendationGap'] == (
            'curriculum_or_assessment_unavailable'
        )

    def test_overview_exposes_next_activity_and_rejects_stale_run(
        self, client: TestClient
    ) -> None:
        goal_id = _create_goal(client)
        path = f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_SKILL_ID}/diagnostic'
        run_id = uuid4()
        start = _post(
            client,
            f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_SKILL_ID}/start',
            _AUTHORIZATION,
            {'entry_key': str(run_id)},
        )
        assert start.status_code == 200, start.text

        current = _get(
            client,
            path,
            headers={**_AUTHORIZATION, 'X-Diagnostic-Run-Id': str(run_id)},
        )
        assert current.status_code == 200, current.text
        body = current.json()
        assert body['runState'] == 'active'
        assert body['readyToComplete'] is False
        assert body['nextActivityId'] is not None
        assert body['pendingAttemptId'] is None

        stale = _get(
            client,
            path,
            headers={**_AUTHORIZATION, 'X-Diagnostic-Run-Id': str(uuid4())},
        )
        assert stale.status_code == 409, stale.text

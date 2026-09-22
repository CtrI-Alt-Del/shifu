from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response


_AUTHENTICATED_USER = AuthenticatedUser(
    account_id='01JACCOUNT000000000000TEST',
    display_name='Learner Test',
    time_zone=None,
)


class TestStartPlanningController:
    def test_missing_bearer_token_returns_safe_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/intelligence/planning-sessions',
                json={'initial_intent': 'Quero aprender inglês'},
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_empty_intent_returns_validation_error(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            _AUTHENTICATED_USER
        )

        with TestClient(app) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/intelligence/planning-sessions',
                    json={'initial_intent': ''},
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 422

    def test_whitespace_only_intent_returns_validation_error(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            _AUTHENTICATED_USER
        )

        with TestClient(app) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/intelligence/planning-sessions',
                    json={'initial_intent': '   '},
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 422

    def test_valid_intent_persists_a_planning_session_and_returns_it(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            _AUTHENTICATED_USER
        )

        with TestClient(app) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/intelligence/planning-sessions',
                    json={
                        'initial_intent': '  Quero aprender inglês em três meses  ',
                    },
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 201
        body = response.json()
        assert body['id']
        assert body['created_at']

        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            persisted = repositories.planning_sessions.find_by_id(body['id'])

        assert persisted is not None
        assert persisted.account_id == _AUTHENTICATED_USER.account_id
        assert persisted.initial_intent == 'Quero aprender inglês em três meses'

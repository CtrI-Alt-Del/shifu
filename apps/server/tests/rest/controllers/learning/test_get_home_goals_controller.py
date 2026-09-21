from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.learning.entities import GoalFaker
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response


class TestGetHomeGoalsController:
    def test_missing_bearer_token_returns_safe_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get('/learning/goals'),  # pyright: ignore[reportUnknownMemberType]
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_returns_only_the_authenticated_accounts_goals_ordered_by_updated_at(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        older_goal = GoalFaker.fake(
            title='Aprender SQL',
            description='Objetivo mais antigo da conta A',
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        newer_goal = GoalFaker.fake(
            account_id=older_goal.account_id,
            title='Aprender Python',
            description='Objetivo mais recente da conta A',
            updated_at=datetime(2026, 1, 3, tzinfo=UTC),
        )
        other_account_goal = GoalFaker.fake(
            title='Objetivo de outra conta',
            description='Nunca deve aparecer para a conta A',
        )
        account_a_id = older_goal.account_id

        database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            repositories.goals.add_many([older_goal, newer_goal, other_account_goal])

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=account_a_id,
                display_name='Pessoa Aprendente',
                time_zone=None,
            )
        )

        with TestClient(app) as client:
            response = cast(
                'Response',
                client.get(  # pyright: ignore[reportUnknownMemberType]
                    '/learning/goals',
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 200
        body = response.json()
        assert [goal['id'] for goal in body['goals']] == [
            newer_goal.id,
            older_goal.id,
        ]
        assert body['goals'][0] == {
            'id': newer_goal.id,
            'title': newer_goal.title,
            'description': newer_goal.description,
            'skill_count': 0,
            'updated_at': newer_goal.updated_at.isoformat(),
        }

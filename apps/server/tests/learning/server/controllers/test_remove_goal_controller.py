from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
	from httpx import Response

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.fakers.learning.entities import GoalFaker
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = SEED_ACCOUNT_ID
OTHER_ACCOUNT = 'other-account-id'


class _TestAuthenticationProvider:
    def __init__(self, account_id: str = SEED_ACCOUNT_ID) -> None:
        self.account_id = account_id

    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=self.account_id,
            display_name='Test User',
            time_zone='America/Sao_Paulo',
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))

    learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.learning_database = SqlalchemyLearningDatabase(
        postgres_database.engine
    )
    application.state.curriculum_content_provider = DatabaseCurriculumContentProvider(
        SqlalchemyCurriculumDatabase(postgres_database.engine)
    )
    yield application
    application.dependency_overrides.clear()


class TestRemoveGoalController:
    def test_should_return_204_when_goal_exists_and_is_owned(
        self,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake(account_id=ACCOUNT_ID)
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        client = TestClient(application)
        response = cast(
            'Response',
            client.delete(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{goal.id}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 204
        assert response.text == ''

    def test_should_return_404_when_goal_belongs_to_another_account(
        self,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake(account_id=OTHER_ACCOUNT)
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        client = TestClient(application)
        response = cast(
            'Response',
            client.delete(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{goal.id}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404

    def test_should_return_404_when_goal_does_not_exist(
        self,
        application: FastAPI,
    ) -> None:
        client = TestClient(application)
        response = cast(
            'Response',
            client.delete(  # pyright: ignore[reportUnknownMemberType]
                '/learning/goals/nonexistent-id',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404

    def test_should_return_401_when_unauthenticated(
        self,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake(account_id=ACCOUNT_ID)
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        client = TestClient(application)
        response = cast(
            'Response',
            client.delete(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{goal.id}'
            ),
        )

        assert response.status_code == 401

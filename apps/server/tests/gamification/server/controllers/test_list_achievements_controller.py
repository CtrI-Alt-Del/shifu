from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
)
from shifu.gamification.core.domain.enums import AchievementCriterionKind
from shifu.gamification.core.domain.structures import AchievementCriterion
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.gamification_database = SqlalchemyGamificationDatabase(
        postgres_database.engine
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestListAchievementsController:
    def test_should_return_catalog_with_obtained_and_locked_states(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID,
                    total_xp=25,
                    level=1,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
            repositories.earned_achievements.try_add(
                EarnedAchievementFaker.fake(
                    account_id=ACCOUNT_ID,
                    achievement_id='primeiro-passo',
                    achievement_name='Primeiro Passo',
                    criterion=AchievementCriterion.create(
                        kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=1
                    ),
                    xp_reward=25,
                    achieved_at=NOW,
                    granted_at=NOW,
                )
            )

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                '/gamification/achievements',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['level'] == 1
        assert body['totalXp'] == 25
        assert len(body['achievements']) == 12
        obtained = [
            achievement
            for achievement in body['achievements']
            if achievement['state'] == 'obtained'
        ]
        locked = [
            achievement
            for achievement in body['achievements']
            if achievement['state'] == 'locked'
        ]
        assert len(obtained) == 1
        assert len(locked) == 11
        assert obtained[0]['code'] == 'primeiro-passo'
        assert obtained[0]['unlockedAt'] is not None
        explorador = next(
            achievement
            for achievement in body['achievements']
            if achievement['code'] == 'explorador'
        )
        assert explorador['state'] == 'locked'
        assert explorador['criterionLabel'] == '5 diagnósticos concluídos'
        assert explorador['xpReward'] == 75

    def test_should_return_zeroed_overview_when_profile_is_absent(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                '/gamification/achievements',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body['level'] == 1
        assert body['totalXp'] == 0
        assert all(
            achievement['state'] == 'locked' for achievement in body['achievements']
        )

    def test_should_reject_unauthenticated_request(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get('/gamification/achievements'),  # pyright: ignore[reportUnknownMemberType]
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

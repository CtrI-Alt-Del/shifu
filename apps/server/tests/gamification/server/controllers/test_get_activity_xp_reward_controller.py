from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import (
    ActivityXpBalanceFaker,
    ActivityXpRecognitionFaker,
    GamificationProfileFaker,
)
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERAC'
ACTIVITY_ID = '01SHF00000000000000ACTIVTY'
GRANTED_ATTEMPT_ID = '01SHF00000000000000ATTEMPA'
PENDING_ATTEMPT_ID = '01SHF00000000000000ATTEMPB'
ZERO_ATTEMPT_ID = '01SHF00000000000000ATTEMPC'
TIME_ZONE = 'America/Sao_Paulo'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token == 'other-access-token':
            return AuthenticatedUser(
                account_id=OTHER_ACCOUNT_ID,
                display_name='Outra Pessoa',
                time_zone=TIME_ZONE,
            )
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone=TIME_ZONE,
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


def _url(activity_id: str, attempt_id: str) -> str:
    return f'/gamification/activities/{activity_id}/attempts/{attempt_id}/xp-reward'


class TestGetActivityXpRewardController:
    @staticmethod
    def _seed_profile(
        postgres_database: PostgresDatabase, account_id: str = ACCOUNT_ID
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=account_id, created_at=NOW, updated_at=NOW
                )
            )

    @staticmethod
    def _seed_granted(postgres_database: PostgresDatabase, account_id: str) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.activity_xp_balances.add(
                ActivityXpBalanceFaker.fake(
                    account_id=account_id,
                    activity_id=ACTIVITY_ID,
                    maximum_xp=10,
                    granted_xp=6,
                    updated_at=NOW,
                )
            )
            repositories.activity_xp_recognitions.try_add(
                ActivityXpRecognitionFaker.fake(
                    account_id=account_id,
                    activity_id=ACTIVITY_ID,
                    attempt_id=GRANTED_ATTEMPT_ID,
                    granted_xp=6,
                    occurred_at=NOW,
                    recognized_at=NOW,
                )
            )
            repositories.activity_xp_recognitions.try_add(
                ActivityXpRecognitionFaker.fake(
                    account_id=account_id,
                    activity_id=ACTIVITY_ID,
                    attempt_id=ZERO_ATTEMPT_ID,
                    granted_xp=0,
                    xp_grant_id=None,
                    occurred_at=NOW,
                    recognized_at=NOW,
                )
            )

    def test_should_return_granted_state_with_persisted_amounts(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed_profile(postgres_database)
        self._seed_granted(postgres_database, ACCOUNT_ID)

        response = client.get(
            _url(ACTIVITY_ID, GRANTED_ATTEMPT_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body == {
            'activityId': ACTIVITY_ID,
            'attemptId': GRANTED_ATTEMPT_ID,
            'state': 'granted',
            'additionalXp': 6,
            'grantedXp': 6,
            'maximumXp': 10,
        }

    def test_should_return_no_additional_state_for_a_zero_recognition(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed_profile(postgres_database)
        self._seed_granted(postgres_database, ACCOUNT_ID)

        response = client.get(
            _url(ACTIVITY_ID, ZERO_ATTEMPT_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['state'] == 'no-additional'
        assert body['additionalXp'] == 0
        assert body['grantedXp'] == 6
        assert body['maximumXp'] == 10

    def test_should_return_pending_for_an_unrecognized_attempt(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed_profile(postgres_database)

        response = client.get(
            _url(ACTIVITY_ID, PENDING_ATTEMPT_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body == {
            'activityId': ACTIVITY_ID,
            'attemptId': PENDING_ATTEMPT_ID,
            'state': 'pending',
            'additionalXp': 0,
            'grantedXp': 0,
            'maximumXp': None,
        }

    def test_should_not_leak_another_accounts_amount_for_the_same_activity(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed_profile(postgres_database, ACCOUNT_ID)
        self._seed_profile(postgres_database, OTHER_ACCOUNT_ID)
        self._seed_granted(postgres_database, OTHER_ACCOUNT_ID)

        response = client.get(
            _url(ACTIVITY_ID, GRANTED_ATTEMPT_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['state'] == 'pending'
        assert body['grantedXp'] == 0
        assert body['maximumXp'] is None

    def test_should_return_not_found_without_a_gamification_profile(
        self, client: TestClient
    ) -> None:
        response = client.get(
            _url(ACTIVITY_ID, GRANTED_ATTEMPT_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 404

    def test_should_reject_an_unauthenticated_request(self, client: TestClient) -> None:
        response = client.get(_url(ACTIVITY_ID, GRANTED_ATTEMPT_ID))

        assert response.status_code == 401

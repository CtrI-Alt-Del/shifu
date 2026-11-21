from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
ANSWERED_AT = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
PRACTICED = PracticeStreak(current=1, longest=1, latest_practice_date=date(2026, 9, 14))
OWNER = {'Authorization': 'Bearer test-access-token'}
OTHER = {'Authorization': 'Bearer other-access-token'}
URL = '/gamification/streak-reminder'


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {
            'test-access-token': ACCOUNT_ID,
            'other-access-token': OTHER_ACCOUNT_ID,
        }
        account_id = accounts.get(access_token)
        if account_id is None:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=account_id,
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


class TestGetStreakReminderController:
    @staticmethod
    def _seed(
        postgres_database: PostgresDatabase,
        account_id: str,
        *,
        streak: PracticeStreak | None = None,
        reminder_hour: int = 18,
        answered_at: datetime | None = None,
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=account_id,
                    streak=streak,
                    reminder_hour=reminder_hour,
                    reminder_invite_answered_at=answered_at,
                    created_at=CREATED_AT,
                )
            )

    def test_should_return_the_default_hour_and_not_eligible_for_a_new_profile(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)

        response = client.get(URL, headers=OWNER)

        assert response.status_code == 200
        assert response.json() == {'hour': 18, 'inviteStatus': 'not-eligible'}

    def test_should_return_pending_after_the_first_recognized_practice_day(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, streak=PRACTICED)

        response = client.get(URL, headers=OWNER)

        assert response.status_code == 200
        assert response.json() == {'hour': 18, 'inviteStatus': 'pending'}

    def test_should_return_the_stored_hour_and_the_answered_status(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(
            postgres_database,
            ACCOUNT_ID,
            streak=PRACTICED,
            reminder_hour=7,
            answered_at=ANSWERED_AT,
        )

        response = client.get(URL, headers=OWNER)

        assert response.status_code == 200
        assert response.json() == {'hour': 7, 'inviteStatus': 'answered'}

    def test_should_not_leak_another_accounts_settings(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, streak=PRACTICED, reminder_hour=7)
        self._seed(
            postgres_database,
            OTHER_ACCOUNT_ID,
            streak=PRACTICED,
            reminder_hour=21,
            answered_at=ANSWERED_AT,
        )

        owner = client.get(URL, headers=OWNER)
        other = client.get(URL, headers=OTHER)

        assert owner.json() == {'hour': 7, 'inviteStatus': 'pending'}
        assert other.json() == {'hour': 21, 'inviteStatus': 'answered'}

    def test_should_answer_not_found_when_the_account_has_no_profile(
        self, client: TestClient
    ) -> None:
        response = client.get(URL, headers=OWNER)

        assert response.status_code == 404

    def test_should_reject_a_request_without_a_session(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, streak=PRACTICED)

        response = client.get(URL)

        assert response.status_code == 401

    def test_should_reject_an_invalid_token(self, client: TestClient) -> None:
        response = client.get(URL, headers={'Authorization': 'Bearer unknown-token'})

        assert response.status_code == 401

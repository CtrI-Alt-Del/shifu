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
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
FIRST_ANSWER = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
LATER_ANSWER = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
STREAK = PracticeStreak(current=1, longest=1, latest_practice_date=date(2026, 9, 14))
OWNER = {'Authorization': 'Bearer test-access-token'}
OTHER = {'Authorization': 'Bearer other-access-token'}
SETTINGS_URL = '/gamification/streak-reminder'
ANSWER_URL = '/gamification/streak-reminder/invite-answer'


class _MutableClockProvider(ClockProvider):
    def __init__(self) -> None:
        self.current: datetime = FIRST_ANSWER

    def now(self) -> datetime:
        return self.current


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
def clock() -> _MutableClockProvider:
    return _MutableClockProvider()


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
    clock: _MutableClockProvider,
) -> Iterator[FastAPI]:
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.gamification_database = SqlalchemyGamificationDatabase(
        postgres_database.engine
    )
    application.dependency_overrides[SharedPipe.get_clock_provider] = lambda: clock
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestAnswerStreakReminderInviteController:
    @staticmethod
    def _seed(postgres_database: PostgresDatabase, account_id: str) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=account_id,
                    total_xp=120,
                    streak=STREAK,
                    reminder_hour=7,
                    created_at=CREATED_AT,
                )
            )

    @staticmethod
    def _stored_answer(
        postgres_database: PostgresDatabase, account_id: str
    ) -> datetime | None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
        assert profile is not None
        return profile.reminder_invite_answered_at

    def test_should_answer_the_invite_and_keep_it_answered_for_a_fresh_read(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)
        assert client.get(SETTINGS_URL, headers=OWNER).json() == {
            'hour': 7,
            'inviteStatus': 'pending',
        }

        response = client.post(ANSWER_URL, headers=OWNER)

        assert response.status_code == 200
        assert response.json() == {'hour': 7, 'inviteStatus': 'answered'}
        assert client.get(SETTINGS_URL, headers=OWNER).json() == {
            'hour': 7,
            'inviteStatus': 'answered',
        }
        assert self._stored_answer(postgres_database, ACCOUNT_ID) == FIRST_ANSWER

    def test_should_stay_answered_and_keep_the_first_answer_when_repeated(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        clock: _MutableClockProvider,
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)
        client.post(ANSWER_URL, headers=OWNER)
        clock.current = LATER_ANSWER

        response = client.post(ANSWER_URL, headers=OWNER)

        assert response.status_code == 200
        assert response.json() == {'hour': 7, 'inviteStatus': 'answered'}
        assert self._stored_answer(postgres_database, ACCOUNT_ID) == FIRST_ANSWER

    def test_should_not_answer_another_accounts_invite(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)
        self._seed(postgres_database, OTHER_ACCOUNT_ID)

        client.post(ANSWER_URL, headers=OWNER)

        assert client.get(SETTINGS_URL, headers=OTHER).json() == {
            'hour': 7,
            'inviteStatus': 'pending',
        }
        assert self._stored_answer(postgres_database, OTHER_ACCOUNT_ID) is None

    def test_should_change_nothing_else_on_the_profile(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)

        client.post(ANSWER_URL, headers=OWNER)

        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(ACCOUNT_ID)
        assert profile is not None
        assert profile.total_xp == 120
        assert profile.streak == STREAK
        assert profile.reminder_hour == 7

    def test_should_answer_not_found_when_the_account_has_no_profile(
        self, client: TestClient
    ) -> None:
        response = client.post(ANSWER_URL, headers=OWNER)

        assert response.status_code == 404

    def test_should_reject_a_request_without_a_session_and_record_nothing(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)

        response = client.post(ANSWER_URL)

        assert response.status_code == 401
        assert self._stored_answer(postgres_database, ACCOUNT_ID) is None

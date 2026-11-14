from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
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


def _practice_day(account_id: str, identifier: str, day: int) -> PracticeDay:
    practiced_at = datetime(2026, 1, day, 15, 0, tzinfo=UTC)
    return PracticeDay.create(
        id=identifier,
        account_id=account_id,
        time_zone=TIME_ZONE,
        practiced_at=practiced_at,
        recognized_at=practiced_at,
    )


class TestGetPracticeCalendarController:
    @staticmethod
    def _seed(postgres_database: PostgresDatabase) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID, created_at=NOW, updated_at=NOW
                )
            )
            repositories.practice_days.try_add(
                _practice_day(ACCOUNT_ID, '01SHF0000000000000PRACTI1', 5)
            )
            repositories.practice_days.try_add(
                _practice_day(ACCOUNT_ID, '01SHF0000000000000PRACTI2', 6)
            )

    def test_should_return_the_month_for_the_owning_account(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/calendar',
            params={'year': 2026, 'month': 1},
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['year'] == 2026
        assert body['month'] == 1
        assert len(body['days']) == 31
        assert body['earliestPracticeDate'] == '2026-01-05'
        states = {item['day']: item['state'] for item in body['days']}
        assert states['2026-01-05'] == 'practiced'
        assert states['2026-01-06'] == 'practiced'
        assert states['2026-01-07'] == 'missed'
        assert body['streak']['longest'] >= 0

    def test_should_persist_and_read_back_through_the_real_migration(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        """The table, model, mapper, repository and migration have no tests of
        their own by rule; this read-back is their proof."""
        self._seed(postgres_database)

        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            dates = repositories.practice_days.find_many_dates_by_account_id(ACCOUNT_ID)

        assert [value.isoformat() for value in dates] == ['2026-01-05', '2026-01-06']

    def test_should_collapse_a_duplicate_date_at_the_database(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            inserted = repositories.practice_days.try_add(
                _practice_day(ACCOUNT_ID, '01SHF0000000000000PRACTI3', 5)
            )

        assert inserted is False
        with database.transaction() as repositories:
            dates = repositories.practice_days.find_many_dates_by_account_id(ACCOUNT_ID)
        assert len(dates) == 2

    def test_should_not_leak_another_accounts_practice_days(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=OTHER_ACCOUNT_ID, created_at=NOW, updated_at=NOW
                )
            )
            repositories.practice_days.try_add(
                _practice_day(OTHER_ACCOUNT_ID, '01SHF0000000000000PRACTI4', 20)
            )

        response = client.get(
            '/gamification/calendar',
            params={'year': 2026, 'month': 1},
            headers={'Authorization': 'Bearer other-access-token'},
        )

        assert response.status_code == 200
        states = {item['day']: item['state'] for item in response.json()['days']}
        assert states['2026-01-20'] == 'practiced'
        assert states['2026-01-05'] == 'neutral'

    def test_should_reject_a_future_month(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/calendar',
            params={'year': 2099, 'month': 1},
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 400

    def test_should_reject_an_out_of_range_month(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/calendar',
            params={'year': 2026, 'month': 13},
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 400

    def test_should_return_the_initial_state_without_a_gamification_profile(
        self, client: TestClient
    ) -> None:
        response = client.get(
            '/gamification/calendar',
            params={'year': 2026, 'month': 1},
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['streak'] == {'current': 0, 'longest': 0}
        assert body['earliestPracticeDate'] is None
        assert len(body['days']) == 31
        assert {item['state'] for item in body['days']} == {'neutral'}

    def test_should_reject_an_unauthenticated_request(self, client: TestClient) -> None:
        response = client.get(
            '/gamification/calendar', params={'year': 2026, 'month': 1}
        )

        assert response.status_code == 401

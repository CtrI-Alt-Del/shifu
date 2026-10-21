from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
)
from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
TIME_ZONE = 'America/Sao_Paulo'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
ACTIVE_CATALOG_SIZE = 12


def _today() -> date:
    """The viewer's local date, resolved exactly as the endpoint resolves it."""
    return datetime.now(UTC).astimezone(ZoneInfo(TIME_ZONE)).date()


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


def _practice_day(account_id: str, identifier: str, day: date) -> PracticeDay:
    practiced_at = datetime.combine(day, time(15, 0), tzinfo=ZoneInfo(TIME_ZONE))
    return PracticeDay.create(
        id=identifier,
        account_id=account_id,
        time_zone=TIME_ZONE,
        practiced_at=practiced_at,
        recognized_at=practiced_at,
    )


class TestGetGamificationOverviewController:
    @staticmethod
    def _seed(postgres_database: PostgresDatabase) -> date:
        today = _today()
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID,
                    total_xp=1240,
                    streak=PracticeStreak(
                        current=2, longest=4, latest_practice_date=today
                    ),
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                )
            )
            repositories.practice_days.try_add(
                _practice_day(ACCOUNT_ID, '01SHF0000000000000PRACTI1', today)
            )
            repositories.practice_days.try_add(
                _practice_day(
                    ACCOUNT_ID,
                    '01SHF0000000000000PRACTI2',
                    today - timedelta(days=1),
                )
            )
            # One day outside the trailing window, to prove it is excluded from
            # the strip while still counting towards the record streak.
            repositories.practice_days.try_add(
                _practice_day(
                    ACCOUNT_ID,
                    '01SHF0000000000000PRACTI3',
                    today - timedelta(days=20),
                )
            )
            for index, achievement_id in enumerate(
                ('primeiro-passo', 'explorador', 'primeiro-dominio', 'em-evolucao')
            ):
                repositories.earned_achievements.try_add(
                    EarnedAchievementFaker.fake(
                        id=f'01SHF000000000000EARNED{index}',
                        account_id=ACCOUNT_ID,
                        achievement_id=achievement_id,
                        achievement_name=f'Conquista {index}',
                        xp_reward=25,
                        achieved_at=datetime(2026, 2, index + 1, tzinfo=UTC),
                        granted_at=datetime(2026, 2, index + 1, tzinfo=UTC),
                    )
                )
        return today

    def test_should_return_the_overview_for_the_owning_account(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        today = self._seed(postgres_database)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['level'] == 5
        assert body['totalXp'] == 1240
        assert body['currentLevelXp'] == 1000
        assert body['nextLevelXp'] == 1500
        assert body['xpForNextLevel'] == 260
        assert body['levelPercentage'] == 48
        assert body['streak']['today'] == today.isoformat()
        assert body['streak']['isTodayPending'] is False
        assert body['streak']['streak'] == {'current': 2, 'longest': 4}

    def test_should_return_exactly_seven_days_ending_today(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        today = self._seed(postgres_database)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        days = response.json()['streak']['lastSevenDays']
        assert [item['day'] for item in days] == [
            (today - timedelta(days=offset)).isoformat()
            for offset in reversed(range(7))
        ]
        assert days[-1]['state'] == 'current-streak'
        assert days[-2]['state'] == 'current-streak'
        assert days[0]['state'] == 'missed'

    def test_should_return_the_three_newest_achievements_and_the_catalog_ratio(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        achievements = response.json()['achievements']
        assert [item['name'] for item in achievements['recent']] == [
            'Conquista 3',
            'Conquista 2',
            'Conquista 1',
        ]
        assert achievements['recent'][0]['achievementId'] == 'em-evolucao'
        assert achievements['recent'][0]['xpReward'] == 25
        assert achievements['recent'][0]['criterionLabel'] == '1 diagnóstico concluído'
        assert achievements['obtainedCount'] == 4
        assert achievements['catalogCount'] == ACTIVE_CATALOG_SIZE

    def test_should_report_the_same_streak_as_the_calendar_read(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        today = self._seed(postgres_database)

        overview = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )
        calendar = client.get(
            '/gamification/calendar',
            params={'year': today.year, 'month': today.month},
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert overview.status_code == 200
        assert calendar.status_code == 200
        assert overview.json()['streak']['streak'] == calendar.json()['streak']

    def test_should_not_leak_another_accounts_overview(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=OTHER_ACCOUNT_ID,
                    total_xp=100,
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                )
            )

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer other-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['level'] == 2
        assert body['totalXp'] == 100
        assert body['achievements']['obtainedCount'] == 0
        assert body['achievements']['recent'] == []
        assert body['streak']['streak'] == {'current': 0, 'longest': 0}

    def test_should_return_the_initial_state_without_a_gamification_profile(
        self, client: TestClient
    ) -> None:
        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert body['level'] == 1
        assert body['totalXp'] == 0
        assert body['xpForNextLevel'] == 100
        assert body['levelPercentage'] == 0
        assert len(body['streak']['lastSevenDays']) == 7
        assert body['achievements'] == {
            'recent': [],
            'obtainedCount': 0,
            'catalogCount': ACTIVE_CATALOG_SIZE,
        }

    def test_should_reject_an_unauthenticated_request(self, client: TestClient) -> None:
        response = client.get('/gamification/overview')

        assert response.status_code == 401

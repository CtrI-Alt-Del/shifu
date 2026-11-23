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
    RewardedMilestoneFaker,
    XpGrantFaker,
)
from shifu.gamification.core.domain.achievement_catalog import ACHIEVEMENT_CATALOG
from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.core.domain.enums import MilestoneKind, XpSource
from shifu.gamification.core.domain.structures import PracticeStreak, XpOrigin
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
TIME_ZONE = 'America/Sao_Paulo'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
ACTIVE_CATALOG_SIZE = 12
_NOW = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
_CURRENT_WEEK_START = date(2026, 10, 19)
_FIRST_WEEK_START = date(2026, 8, 3)


def _today() -> date:
    """The viewer's local date, resolved exactly as the endpoint resolves it."""
    return _NOW.astimezone(ZoneInfo(TIME_ZONE)).date()


class _FixedClockProvider(ClockProvider):
    def now(self) -> datetime:
        return _NOW


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
    application.dependency_overrides[SharedPipe.get_clock_provider] = lambda: (
        _FixedClockProvider()
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
            # The first day of the month, apart from the current run.
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
        assert body['streak']['streak'] == {'current': 2, 'longest': 4}

    def test_should_not_expose_the_removed_streak_members(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        streak = response.json()['streak']
        assert 'lastSevenDays' not in streak
        assert 'isTodayPending' not in streak
        assert set(streak) == {'streak', 'currentMonth', 'today'}

    def test_should_return_every_day_of_the_current_local_month(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        today = self._seed(postgres_database)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        days = response.json()['streak']['currentMonth']
        assert [item['day'] for item in days] == [
            date(today.year, today.month, number).isoformat() for number in range(1, 32)
        ]
        states = {item['day']: item['state'] for item in days}
        assert states[today.isoformat()] == 'current-streak'
        assert states[(today - timedelta(days=1)).isoformat()] == 'current-streak'
        assert states[date(2026, 10, 1).isoformat()] == 'practiced'
        assert states[date(2026, 10, 10).isoformat()] == 'missed'
        assert states[date(2026, 10, 31).isoformat()] == 'neutral'

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

    def test_should_return_the_next_achievement_with_a_clamped_current_value(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        # The longest streak (4) exceeds Consistência I's target (3) and the
        # level criterion is also fully met: both clamp to a full proportion,
        # so the earlier catalog entry wins and its current value stays at 3.
        assert response.json()['achievements']['nextAchievement'] == {
            'achievementId': 'consistencia-i',
            'name': 'Consistência I',
            'criterionLabel': '3 dias consecutivos',
            'criterionKind': 'longest_streak',
            'xpReward': 25,
            'progressCurrent': 3,
            'progressTarget': 3,
        }

    def test_should_count_milestones_from_the_database_for_the_next_achievement(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID,
                    total_xp=0,
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                )
            )
            for index, achievement in enumerate(ACHIEVEMENT_CATALOG):
                if achievement.id == 'em-evolucao':
                    continue
                repositories.earned_achievements.try_add(
                    EarnedAchievementFaker.fake(
                        id=f'01SHF000000000000EARNED{index:02d}',
                        account_id=ACCOUNT_ID,
                        achievement_id=achievement.id,
                        achievement_name=achievement.name,
                        achieved_at=datetime(2026, 2, 1, tzinfo=UTC),
                        granted_at=datetime(2026, 2, 1, tzinfo=UTC),
                    )
                )
            for _ in range(3):
                repositories.rewarded_milestones.try_add(
                    RewardedMilestoneFaker.fake(
                        account_id=ACCOUNT_ID,
                        kind=MilestoneKind.COMPETENCY_MASTERY,
                        occurred_at=datetime(2026, 2, 1, tzinfo=UTC),
                    )
                )
            repositories.rewarded_milestones.try_add(
                RewardedMilestoneFaker.fake(
                    account_id=OTHER_ACCOUNT_ID,
                    kind=MilestoneKind.COMPETENCY_MASTERY,
                    occurred_at=datetime(2026, 2, 1, tzinfo=UTC),
                )
            )

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        next_achievement = response.json()['achievements']['nextAchievement']
        assert next_achievement['achievementId'] == 'em-evolucao'
        assert next_achievement['progressCurrent'] == 3
        assert next_achievement['progressTarget'] == 10

    def test_should_return_no_next_achievement_when_every_active_one_is_obtained(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            for index, achievement in enumerate(ACHIEVEMENT_CATALOG):
                repositories.earned_achievements.try_add(
                    EarnedAchievementFaker.fake(
                        id=f'01SHF000000000000EARNED{index:02d}',
                        account_id=ACCOUNT_ID,
                        achievement_id=achievement.id,
                        achievement_name=achievement.name,
                        achieved_at=datetime(2026, 2, 1, tzinfo=UTC),
                        granted_at=datetime(2026, 2, 1, tzinfo=UTC),
                    )
                )

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        achievements = response.json()['achievements']
        assert achievements['nextAchievement'] is None
        assert achievements['obtainedCount'] == ACTIVE_CATALOG_SIZE

    def test_should_return_twelve_local_weeks_of_xp_by_fact_date(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            for grant in (
                # Fact in the week of Oct 12, granted a week later.
                XpGrantFaker.fake(
                    account_id=ACCOUNT_ID,
                    amount=20,
                    occurred_at=datetime(2026, 10, 14, 15, 0, tzinfo=UTC),
                    granted_at=datetime(2026, 10, 21, 9, 0, tzinfo=UTC),
                ),
                # Sunday 23:30 and Monday 00:30 in America/Sao_Paulo.
                XpGrantFaker.fake(
                    account_id=ACCOUNT_ID,
                    amount=10,
                    occurred_at=datetime(2026, 10, 19, 2, 30, tzinfo=UTC),
                ),
                XpGrantFaker.fake(
                    account_id=ACCOUNT_ID,
                    amount=4,
                    occurred_at=datetime(2026, 10, 19, 3, 30, tzinfo=UTC),
                ),
                # First instant of the window, and one second before it.
                XpGrantFaker.fake(
                    account_id=ACCOUNT_ID,
                    amount=3,
                    occurred_at=datetime(2026, 8, 3, 3, 0, tzinfo=UTC),
                ),
                XpGrantFaker.fake(
                    account_id=ACCOUNT_ID,
                    amount=99,
                    occurred_at=datetime(2026, 8, 3, 2, 59, 59, tzinfo=UTC),
                ),
                XpGrantFaker.fake(
                    account_id=OTHER_ACCOUNT_ID,
                    amount=500,
                    occurred_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                ),
            ):
                repositories.xp_grants.add(grant)

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        weekly_xp = response.json()['weeklyXp']
        assert len(weekly_xp) == 12
        assert weekly_xp[0] == {'weekStart': _FIRST_WEEK_START.isoformat(), 'xp': 3}
        assert weekly_xp[-1] == {
            'weekStart': _CURRENT_WEEK_START.isoformat(),
            'xp': 4,
        }
        by_week = {item['weekStart']: item['xp'] for item in weekly_xp}
        assert by_week['2026-10-12'] == 30
        assert sum(by_week.values()) == 37
        assert [item['weekStart'] for item in weekly_xp] == [
            (_FIRST_WEEK_START + timedelta(weeks=offset)).isoformat()
            for offset in range(12)
        ]

    def test_should_keep_counting_xp_earned_in_an_experience_that_no_longer_exists(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID,
                    total_xp=1240,
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                )
            )
            repositories.xp_grants.add(
                XpGrantFaker.fake(
                    account_id=ACCOUNT_ID,
                    amount=25,
                    origin=XpOrigin(
                        source=XpSource.ACTIVITY,
                        reference_id='01SHF0000000000000REFERENC',
                        label='Atividade de aprendizagem',
                        skill_experience_id='01SHF0000000000000REMOVED',
                    ),
                    occurred_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                )
            )

        response = client.get(
            '/gamification/overview',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        body = response.json()
        assert body['totalXp'] == 1240
        assert body['weeklyXp'][-1] == {
            'weekStart': _CURRENT_WEEK_START.isoformat(),
            'xp': 25,
        }

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
        assert (
            body['achievements']['nextAchievement']['achievementId'] == 'ascendente-i'
        )
        assert body['achievements']['nextAchievement']['progressCurrent'] == 2
        assert [item['xp'] for item in body['weeklyXp']] == [0] * 12

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
        assert len(body['streak']['currentMonth']) == 31
        assert body['achievements'] == {
            'recent': [],
            'obtainedCount': 0,
            'catalogCount': ACTIVE_CATALOG_SIZE,
            'nextAchievement': {
                'achievementId': 'ascendente-i',
                'name': 'Ascendente I',
                'criterionLabel': 'nível 5',
                'criterionKind': 'level',
                'xpReward': 50,
                'progressCurrent': 1,
                'progressTarget': 5,
            },
        }
        assert [item['xp'] for item in body['weeklyXp']] == [0] * 12

    def test_should_reject_an_unauthenticated_request(self, client: TestClient) -> None:
        response = client.get('/gamification/overview')

        assert response.status_code == 401

from datetime import UTC, date, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
)
from shifu.gamification.core.domain.enums import (
    AchievementCriterionKind,
    CalendarDayState,
)
from shifu.gamification.core.domain.structures import (
    AchievementCriterion,
    GamificationOverview,
    PracticeStreak,
)
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import (
    GetGamificationOverviewUseCase,
    GetPracticeCalendarUseCase,
)

ACCOUNT_ID = 'account-1'
SAO_PAULO = 'America/Sao_Paulo'
NOON = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
TODAY = date(2026, 9, 15)
ACTIVE_CATALOG_SIZE = 12


class TestGetGamificationOverviewUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self._given_profile(total_xp=0)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = ()
        self.repositories.earned_achievements.find_many_by_account_id.return_value = ()
        self.subject = GetGamificationOverviewUseCase(self.database)

    def _given_profile(
        self,
        *,
        total_xp: int,
        level: int | None = None,
        streak: PracticeStreak | None = None,
    ) -> None:
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID,
                total_xp=total_xp,
                level=level,
                streak=streak,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    def _given_practice_days(self, *days: date) -> None:
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            days
        )

    def _read(
        self, *, now: datetime = NOON, time_zone: str | None = 'UTC'
    ) -> GamificationOverview:
        return self.subject.execute(ACCOUNT_ID, time_zone=time_zone, now=now)

    @staticmethod
    def _states(overview: GamificationOverview) -> list[CalendarDayState]:
        return [item.state for item in overview.streak.last_seven_days]

    def test_should_report_the_initial_state_for_an_account_with_no_reward(
        self,
    ) -> None:
        overview = self._read()

        assert overview.level == 1
        assert overview.total_xp == 0
        assert overview.current_level_xp == 0
        assert overview.next_level_xp == 100
        assert overview.xp_for_next_level == 100
        assert overview.level_percentage == 0
        assert overview.streak.streak == PracticeStreak()
        assert self._states(overview) == [CalendarDayState.NEUTRAL] * 7
        assert overview.achievements.recent == ()
        assert overview.achievements.obtained_count == 0
        assert overview.achievements.catalog_count == ACTIVE_CATALOG_SIZE

    def test_should_report_the_initial_state_when_no_profile_row_exists(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        overview = self._read()

        assert overview.level == 1
        assert overview.total_xp == 0
        assert overview.current_level_xp == 0
        assert overview.next_level_xp == 100
        assert overview.xp_for_next_level == 100
        assert overview.level_percentage == 0
        assert overview.streak.streak == PracticeStreak()
        assert overview.achievements.obtained_count == 0

    def test_should_report_the_reference_level_progress_case(self) -> None:
        self._given_profile(total_xp=1240)

        overview = self._read()

        assert overview.level == 5
        assert overview.total_xp == 1240
        assert overview.current_level_xp == 1000
        assert overview.next_level_xp == 1500
        assert overview.xp_for_next_level == 260
        assert overview.level_percentage == 48

    def test_should_report_the_stored_level_after_a_multi_level_concession(
        self,
    ) -> None:
        self._given_profile(total_xp=5000)

        overview = self._read()

        assert overview.level == 10
        assert overview.current_level_xp == 4500
        assert overview.next_level_xp == 5500
        assert overview.xp_for_next_level == 500
        assert overview.level_percentage == 50

    def test_should_keep_a_preserved_level_above_the_curve_with_zero_progress(
        self,
    ) -> None:
        self._given_profile(total_xp=1240, level=7)

        overview = self._read()

        assert overview.level == 7
        assert overview.current_level_xp == 2100
        assert overview.next_level_xp == 2800
        assert overview.xp_for_next_level == 1560
        assert overview.level_percentage == 0

    def test_should_report_zero_progress_at_exactly_the_level_minimum(self) -> None:
        self._given_profile(total_xp=1000)

        overview = self._read()

        assert overview.level == 5
        assert overview.current_level_xp == 1000
        assert overview.xp_for_next_level == 500
        assert overview.level_percentage == 0

    def test_should_report_one_xp_remaining_just_below_the_next_threshold(self) -> None:
        self._given_profile(total_xp=1499)

        overview = self._read()

        assert overview.level == 5
        assert overview.xp_for_next_level == 1
        assert overview.level_percentage == 99

    def test_should_keep_a_run_ending_yesterday_active_with_today_pending(self) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(
                current=3, longest=3, latest_practice_date=date(2026, 9, 14)
            ),
        )
        self._given_practice_days(
            date(2026, 9, 12), date(2026, 9, 13), date(2026, 9, 14)
        )

        overview = self._read()

        assert overview.streak.streak.current == 3
        assert overview.streak.streak.longest == 3
        assert overview.streak.is_today_pending is True
        assert self._states(overview) == [
            CalendarDayState.NEUTRAL,
            CalendarDayState.NEUTRAL,
            CalendarDayState.NEUTRAL,
            CalendarDayState.CURRENT_STREAK,
            CalendarDayState.CURRENT_STREAK,
            CalendarDayState.CURRENT_STREAK,
            CalendarDayState.TODAY_PENDING,
        ]

    def test_should_report_a_broken_run_as_zero_while_keeping_the_record(self) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(
                current=5, longest=5, latest_practice_date=date(2026, 9, 13)
            ),
        )
        self._given_practice_days(
            date(2026, 9, 9),
            date(2026, 9, 10),
            date(2026, 9, 11),
            date(2026, 9, 12),
            date(2026, 9, 13),
        )

        overview = self._read()

        assert overview.streak.streak.current == 0
        assert overview.streak.streak.longest == 5
        assert overview.streak.is_today_pending is True

    def test_should_mark_today_as_practiced_when_a_day_exists_for_today(self) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(current=1, longest=1, latest_practice_date=TODAY),
        )
        self._given_practice_days(TODAY)

        overview = self._read()

        assert overview.streak.streak.current == 1
        assert overview.streak.is_today_pending is False
        assert overview.streak.last_seven_days[-1].state == (
            CalendarDayState.CURRENT_STREAK
        )

    def test_should_build_a_seven_day_window_across_a_month_boundary(self) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(
                current=0, longest=3, latest_practice_date=date(2026, 9, 1)
            ),
        )
        self._given_practice_days(
            date(2026, 8, 30), date(2026, 8, 31), date(2026, 9, 1)
        )

        overview = self._read(now=datetime(2026, 9, 3, 12, 0, tzinfo=UTC))

        assert [item.day for item in overview.streak.last_seven_days] == [
            date(2026, 8, 28),
            date(2026, 8, 29),
            date(2026, 8, 30),
            date(2026, 8, 31),
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 3),
        ]
        assert self._states(overview) == [
            CalendarDayState.NEUTRAL,
            CalendarDayState.NEUTRAL,
            CalendarDayState.PRACTICED,
            CalendarDayState.PRACTICED,
            CalendarDayState.PRACTICED,
            CalendarDayState.MISSED,
            CalendarDayState.TODAY_PENDING,
        ]

    def test_should_end_the_window_on_today_and_hold_exactly_seven_days(self) -> None:
        overview = self._read()

        assert len(overview.streak.last_seven_days) == 7
        assert overview.streak.today == TODAY
        assert overview.streak.last_seven_days[-1].day == TODAY
        assert overview.streak.last_seven_days[0].day == TODAY - timedelta(days=6)

    def test_should_resolve_today_in_the_accounts_own_time_zone(self) -> None:
        overview = self._read(
            now=datetime(2026, 9, 15, 2, 30, tzinfo=UTC), time_zone=SAO_PAULO
        )

        assert overview.streak.today == date(2026, 9, 14)

    @pytest.mark.parametrize('time_zone', [None, '', 'Not/AZone'])
    def test_should_fall_back_to_utc_for_an_unusable_time_zone(
        self, time_zone: str | None
    ) -> None:
        overview = self._read(
            now=datetime(2026, 9, 15, 2, 30, tzinfo=UTC), time_zone=time_zone
        )

        assert overview.streak.today == TODAY
        assert overview.streak.is_today_pending is True

    def test_should_report_the_three_newest_achievements_in_order(self) -> None:
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            tuple(
                EarnedAchievementFaker.fake(
                    id=f'earned-{index}',
                    account_id=ACCOUNT_ID,
                    achievement_id=f'achievement-{index}',
                    achievement_name=f'Conquista {index}',
                    xp_reward=25,
                    achieved_at=datetime(2026, 9, index + 1, tzinfo=UTC),
                    granted_at=datetime(2026, 9, index + 1, tzinfo=UTC),
                )
                for index in range(5)
            )
        )

        overview = self._read()

        assert [item.name for item in overview.achievements.recent] == [
            'Conquista 4',
            'Conquista 3',
            'Conquista 2',
        ]
        assert [item.achieved_at for item in overview.achievements.recent] == [
            datetime(2026, 9, 5, tzinfo=UTC),
            datetime(2026, 9, 4, tzinfo=UTC),
            datetime(2026, 9, 3, tzinfo=UTC),
        ]

    def test_should_carry_each_achievements_own_stored_text_and_reward(self) -> None:
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            EarnedAchievementFaker.fake(
                account_id=ACCOUNT_ID,
                achievement_id='consistencia-ii',
                achievement_name='Consistência II',
                criterion=AchievementCriterion.create(
                    kind=AchievementCriterionKind.LONGEST_STREAK, target=7
                ),
                xp_reward=50,
                achieved_at=datetime(2026, 9, 10, tzinfo=UTC),
                granted_at=datetime(2026, 9, 10, tzinfo=UTC),
            ),
        )

        recent = self._read().achievements.recent

        assert len(recent) == 1
        assert recent[0].achievement_id == 'consistencia-ii'
        assert recent[0].name == 'Consistência II'
        assert recent[0].criterion_label == '7 dias consecutivos'
        assert recent[0].xp_reward == 50
        assert recent[0].achieved_at == datetime(2026, 9, 10, tzinfo=UTC)

    def test_should_order_achievements_sharing_one_instant_deterministically(
        self,
    ) -> None:
        shared = datetime(2026, 9, 10, tzinfo=UTC)
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            EarnedAchievementFaker.fake(
                id='earned-a',
                account_id=ACCOUNT_ID,
                achievement_id='primeiro-passo',
                achievement_name='Primeiro Passo',
                achieved_at=shared,
                granted_at=shared,
            ),
            EarnedAchievementFaker.fake(
                id='earned-b',
                account_id=ACCOUNT_ID,
                achievement_id='primeiro-dominio',
                achievement_name='Primeiro Domínio',
                achieved_at=shared,
                granted_at=shared,
            ),
        )

        first = [item.name for item in self._read().achievements.recent]
        second = [item.name for item in self._read().achievements.recent]

        assert first == second
        assert sorted(first) == ['Primeiro Domínio', 'Primeiro Passo']

    def test_should_exclude_a_retired_holding_from_the_catalog_ratio(self) -> None:
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            EarnedAchievementFaker.fake(
                id='earned-retired',
                account_id=ACCOUNT_ID,
                achievement_id='conquista-retirada',
                achievement_name='Conquista Retirada',
                achieved_at=datetime(2026, 9, 11, tzinfo=UTC),
                granted_at=datetime(2026, 9, 11, tzinfo=UTC),
            ),
            EarnedAchievementFaker.fake(
                id='earned-active',
                account_id=ACCOUNT_ID,
                achievement_id='primeiro-passo',
                achievement_name='Primeiro Passo',
                achieved_at=datetime(2026, 9, 10, tzinfo=UTC),
                granted_at=datetime(2026, 9, 10, tzinfo=UTC),
            ),
        )

        overview = self._read()

        assert [item.name for item in overview.achievements.recent] == [
            'Conquista Retirada',
            'Primeiro Passo',
        ]
        assert overview.achievements.obtained_count == 1
        assert overview.achievements.catalog_count == ACTIVE_CATALOG_SIZE

    def test_should_report_the_same_streak_values_as_the_practice_calendar(
        self,
    ) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(
                current=3, longest=9, latest_practice_date=date(2026, 9, 14)
            ),
        )
        self._given_practice_days(
            date(2026, 9, 12), date(2026, 9, 13), date(2026, 9, 14)
        )

        overview = self._read()
        calendar = GetPracticeCalendarUseCase(self.database).execute(
            ACCOUNT_ID, 2026, 9, time_zone='UTC', now=NOON
        )

        assert overview.streak.streak == calendar.streak
        assert overview.streak.today == calendar.today

    def test_should_scope_every_read_to_the_requested_account(self) -> None:
        self._read()

        self.repositories.profiles.find_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.practice_days.find_many_dates_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.earned_achievements.find_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )

    def test_should_never_write_on_the_read_path(self) -> None:
        self._given_practice_days(date(2026, 9, 14))
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            EarnedAchievementFaker.fake(account_id=ACCOUNT_ID),
        )

        self._read()

        self.repositories.profiles.update.assert_not_called()
        self.repositories.profiles.add.assert_not_called()
        self.repositories.practice_days.try_add.assert_not_called()
        self.repositories.earned_achievements.try_add.assert_not_called()
        self.repositories.xp_grants.add.assert_not_called()

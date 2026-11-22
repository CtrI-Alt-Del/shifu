from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from itertools import pairwise
from unittest.mock import create_autospec
from zoneinfo import ZoneInfo

import pytest

from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
    XpGrantFaker,
)
from shifu.gamification.core.domain.achievement_catalog import ACHIEVEMENT_CATALOG
from shifu.gamification.core.domain.entities import EarnedAchievement, XpGrant
from shifu.gamification.core.domain.enums import (
    AchievementCriterionKind,
    CalendarDayState,
    MilestoneKind,
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
    ListAchievementsUseCase,
)

ACCOUNT_ID = 'account-1'
SAO_PAULO = 'America/Sao_Paulo'
NOON = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
TODAY = date(2026, 9, 15)
ACTIVE_CATALOG_SIZE = 12
CURRENT_WEEK_START = date(2026, 9, 14)
FIRST_WEEK_START = date(2026, 6, 29)


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
        self._given_milestone_counts()
        self.repositories.xp_grants.find_many_by_account_id_occurred_since.return_value = ()
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

    def _given_milestone_counts(
        self, *, diagnosis: int = 0, competency_mastery: int = 0, skill: int = 0
    ) -> None:
        counts = {
            MilestoneKind.DIAGNOSIS: diagnosis,
            MilestoneKind.COMPETENCY_MASTERY: competency_mastery,
            MilestoneKind.SKILL_COMPLETION: skill,
        }

        def count(account_id: str, kind: MilestoneKind) -> int:
            return counts[kind]

        self.repositories.rewarded_milestones.count_by_account_id_and_kind.side_effect = count

    def _given_every_achievement_obtained_except(self, *kept_locked: str) -> None:
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            tuple(
                self._earned(achievement.id)
                for achievement in ACHIEVEMENT_CATALOG
                if achievement.is_active and achievement.id not in kept_locked
            )
        )

    @staticmethod
    def _earned(achievement_id: str) -> EarnedAchievement:
        return EarnedAchievementFaker.fake(
            account_id=ACCOUNT_ID,
            achievement_id=achievement_id,
            achievement_name=achievement_id,
            achieved_at=datetime(2026, 9, 1, tzinfo=UTC),
        )

    def _given_grants(self, *grants: XpGrant) -> None:
        self.repositories.xp_grants.find_many_by_account_id_occurred_since.return_value = grants

    @staticmethod
    def _grant(
        amount: int, *, occurred_at: datetime, granted_at: datetime | None = None
    ) -> XpGrant:
        return XpGrantFaker.fake(
            account_id=ACCOUNT_ID,
            amount=amount,
            occurred_at=occurred_at,
            granted_at=granted_at,
        )

    def _read(
        self, *, now: datetime = NOON, time_zone: str | None = 'UTC'
    ) -> GamificationOverview:
        return self.subject.execute(ACCOUNT_ID, time_zone=time_zone, now=now)

    @staticmethod
    def _states(overview: GamificationOverview) -> list[CalendarDayState]:
        return [item.state for item in overview.streak.current_month]

    @staticmethod
    def _state_of(overview: GamificationOverview, day: date) -> CalendarDayState:
        return next(
            item.state for item in overview.streak.current_month if item.day == day
        )

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
        assert self._states(overview) == [CalendarDayState.NEUTRAL] * 30
        assert overview.achievements.recent == ()
        assert overview.achievements.obtained_count == 0
        assert overview.achievements.catalog_count == ACTIVE_CATALOG_SIZE
        assert [item.xp for item in overview.weekly_xp] == [0] * 12

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
        assert self._states(overview) == (
            [CalendarDayState.NEUTRAL] * 11
            + [CalendarDayState.CURRENT_STREAK] * 3
            + [CalendarDayState.TODAY_PENDING]
            + [CalendarDayState.NEUTRAL] * 15
        )

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
        assert self._state_of(overview, TODAY) is CalendarDayState.TODAY_PENDING
        assert self._state_of(overview, date(2026, 9, 13)) is CalendarDayState.PRACTICED
        assert self._state_of(overview, date(2026, 9, 14)) is CalendarDayState.MISSED

    def test_should_mark_today_as_practiced_when_a_day_exists_for_today(self) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(current=1, longest=1, latest_practice_date=TODAY),
        )
        self._given_practice_days(TODAY)

        overview = self._read()

        assert overview.streak.streak.current == 1
        assert self._state_of(overview, TODAY) is CalendarDayState.CURRENT_STREAK
        assert CalendarDayState.TODAY_PENDING not in self._states(overview)

    def test_should_list_only_the_current_month_when_practice_spans_two_months(
        self,
    ) -> None:
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

        assert overview.streak.current_month[0].day == date(2026, 9, 1)
        assert overview.streak.current_month[-1].day == date(2026, 9, 30)
        assert self._states(overview)[:4] == [
            CalendarDayState.PRACTICED,
            CalendarDayState.MISSED,
            CalendarDayState.TODAY_PENDING,
            CalendarDayState.NEUTRAL,
        ]

    def test_should_not_start_any_state_before_the_first_practice_day(self) -> None:
        self._given_practice_days(date(2026, 9, 10), date(2026, 9, 11))

        overview = self._read()

        assert self._states(overview)[:9] == [CalendarDayState.NEUTRAL] * 9
        assert self._state_of(overview, date(2026, 9, 10)) is CalendarDayState.PRACTICED
        assert self._state_of(overview, date(2026, 9, 12)) is CalendarDayState.MISSED
        assert self._state_of(overview, date(2026, 9, 16)) is CalendarDayState.NEUTRAL

    @pytest.mark.parametrize(
        ('now', 'first_weekday', 'first_day', 'last_day'),
        [
            (
                datetime(2026, 2, 10, 12, 0, tzinfo=UTC),
                'Sunday',
                date(2026, 2, 1),
                date(2026, 2, 28),
            ),
            (
                datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
                'Monday',
                date(2026, 6, 1),
                date(2026, 6, 30),
            ),
            (
                datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
                'Tuesday',
                date(2026, 9, 1),
                date(2026, 9, 30),
            ),
            (
                datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
                'Saturday',
                date(2026, 8, 1),
                date(2026, 8, 31),
            ),
            (
                datetime(2028, 2, 29, 12, 0, tzinfo=UTC),
                'Tuesday',
                date(2028, 2, 1),
                date(2028, 2, 29),
            ),
        ],
    )
    def test_should_return_every_day_of_a_month_starting_on_any_weekday(
        self,
        now: datetime,
        first_weekday: str,
        first_day: date,
        last_day: date,
    ) -> None:
        overview = self._read(now=now)

        days = [item.day for item in overview.streak.current_month]
        assert first_day.strftime('%A') == first_weekday
        assert days[0] == first_day
        assert days[-1] == last_day
        assert days == [
            first_day + timedelta(days=offset)
            for offset in range((last_day - first_day).days + 1)
        ]
        assert overview.streak.today in days

    def test_should_carry_no_day_beyond_the_calendar_states(self) -> None:
        overview = self._read()

        assert overview.streak.today == TODAY
        assert {item.state for item in overview.streak.current_month} == {
            CalendarDayState.NEUTRAL
        }

    def test_should_resolve_today_in_the_accounts_own_time_zone(self) -> None:
        overview = self._read(
            now=datetime(2026, 9, 15, 2, 30, tzinfo=UTC), time_zone=SAO_PAULO
        )

        assert overview.streak.today == date(2026, 9, 14)

    def test_should_resolve_the_month_in_the_accounts_own_time_zone(self) -> None:
        overview = self._read(
            now=datetime(2026, 10, 1, 2, 30, tzinfo=UTC), time_zone=SAO_PAULO
        )

        assert overview.streak.today == date(2026, 9, 30)
        assert overview.streak.current_month[0].day == date(2026, 9, 1)
        assert overview.streak.current_month[-1].day == date(2026, 9, 30)

    @pytest.mark.parametrize('time_zone', [None, '', 'Not/AZone'])
    def test_should_fall_back_to_utc_for_an_unusable_time_zone(
        self, time_zone: str | None
    ) -> None:
        overview = self._read(
            now=datetime(2026, 9, 15, 2, 30, tzinfo=UTC), time_zone=time_zone
        )

        assert overview.streak.today == TODAY
        assert self._state_of(overview, TODAY) is CalendarDayState.NEUTRAL
        assert overview.weekly_xp[-1].week_start == CURRENT_WEEK_START

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
        assert [
            call.args
            for call in self.repositories.rewarded_milestones.count_by_account_id_and_kind.call_args_list
        ] == [(ACCOUNT_ID, kind) for kind in MilestoneKind]
        self.repositories.xp_grants.find_many_by_account_id_occurred_since.assert_called_once_with(
            ACCOUNT_ID, datetime(2026, 6, 29, tzinfo=UTC)
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
        self.repositories.rewarded_milestones.try_add.assert_not_called()

    def test_should_pick_the_new_accounts_ascendente_i_at_one_of_five(self) -> None:
        overview = self._read()

        next_achievement = overview.achievements.next_achievement
        assert next_achievement is not None
        assert next_achievement.achievement_id == 'ascendente-i'
        assert next_achievement.name == 'Ascendente I'
        assert next_achievement.criterion_kind is AchievementCriterionKind.LEVEL
        assert next_achievement.criterion_label == 'nível 5'
        assert next_achievement.xp_reward == 50
        assert next_achievement.progress_current == 1
        assert next_achievement.progress_target == 5

    def test_should_pick_the_highest_proportion_among_locked_achievements(
        self,
    ) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(
                current=0, longest=12, latest_practice_date=date(2026, 9, 1)
            ),
        )
        self._given_milestone_counts(competency_mastery=5)
        self._given_every_achievement_obtained_except(
            'consistencia-iii', 'em-evolucao', 'ascendente-i'
        )

        next_achievement = self._read().achievements.next_achievement

        assert next_achievement is not None
        assert next_achievement.achievement_id == 'em-evolucao'
        assert next_achievement.progress_current == 5
        assert next_achievement.progress_target == 10

    def test_should_break_a_proportion_tie_by_catalog_order(self) -> None:
        self._given_profile(
            total_xp=0,
            streak=PracticeStreak(
                current=0, longest=12, latest_practice_date=date(2026, 9, 1)
            ),
        )
        self._given_milestone_counts(diagnosis=2)
        self._given_every_achievement_obtained_except('consistencia-iii', 'explorador')

        next_achievement = self._read().achievements.next_achievement

        assert next_achievement is not None
        assert next_achievement.achievement_id == 'explorador'
        assert (
            next_achievement.progress_current,
            next_achievement.progress_target,
        ) == (
            2,
            5,
        )

    def test_should_clamp_the_current_value_to_the_target(self) -> None:
        self._given_profile(total_xp=0, level=7)
        self._given_every_achievement_obtained_except('ascendente-i', 'ascendente-ii')

        next_achievement = self._read().achievements.next_achievement

        assert next_achievement is not None
        assert next_achievement.achievement_id == 'ascendente-i'
        assert next_achievement.progress_current == 5
        assert next_achievement.progress_target == 5

    def test_should_rank_a_reached_but_unrecognized_criterion_first(self) -> None:
        self._given_milestone_counts(diagnosis=4)
        self._given_every_achievement_obtained_except('ascendente-i', 'primeiro-passo')

        next_achievement = self._read().achievements.next_achievement

        assert next_achievement is not None
        assert next_achievement.achievement_id == 'primeiro-passo'
        assert next_achievement.progress_current == 1
        assert next_achievement.progress_target == 1

    def test_should_report_no_next_achievement_when_every_active_one_is_obtained(
        self,
    ) -> None:
        self._given_every_achievement_obtained_except()

        overview = self._read()

        assert overview.achievements.next_achievement is None
        assert overview.achievements.obtained_count == ACTIVE_CATALOG_SIZE

    def test_should_use_the_same_progress_values_as_the_achievements_list(
        self,
    ) -> None:
        self._given_profile(
            total_xp=300,
            streak=PracticeStreak(
                current=0, longest=4, latest_practice_date=date(2026, 9, 1)
            ),
        )
        self._given_milestone_counts(diagnosis=3, competency_mastery=7, skill=2)
        self.repositories.earned_achievements.find_many_by_account_id.return_value = (
            self._earned('primeiro-passo'),
        )

        listing = ListAchievementsUseCase(self.database).execute(ACCOUNT_ID)
        next_achievement = self._read().achievements.next_achievement

        locked = {
            entry.code: (entry.progress_current, entry.progress_target)
            for entry in listing.achievements
            if entry.state == 'locked'
        }
        assert next_achievement is not None
        listed_current, listed_target = locked[next_achievement.achievement_id]
        assert listed_current is not None
        assert listed_target is not None
        assert (
            next_achievement.progress_current,
            next_achievement.progress_target,
        ) == (
            min(listed_current, listed_target),
            listed_target,
        )
        best = max(
            Fraction(min(current or 0, target or 1), target or 1)
            for current, target in locked.values()
        )
        assert (
            Fraction(
                next_achievement.progress_current, next_achievement.progress_target
            )
            == best
        )

    def test_should_report_exactly_twelve_local_mondays_ending_with_the_current_week(
        self,
    ) -> None:
        weeks = self._read().weekly_xp

        assert len(weeks) == 12
        assert weeks[0].week_start == FIRST_WEEK_START
        assert weeks[-1].week_start == CURRENT_WEEK_START
        assert all(week.week_start.weekday() == 0 for week in weeks)
        assert [
            (later.week_start - earlier.week_start).days
            for earlier, later in pairwise(weeks)
        ] == [7] * 11

    def test_should_sum_grants_by_the_week_of_the_fact_date_not_the_grant_date(
        self,
    ) -> None:
        self._given_grants(
            self._grant(
                20,
                occurred_at=datetime(2026, 9, 9, 15, 0, tzinfo=UTC),
                granted_at=datetime(2026, 9, 15, 9, 0, tzinfo=UTC),
            ),
            self._grant(5, occurred_at=datetime(2026, 9, 8, 10, 0, tzinfo=UTC)),
            self._grant(7, occurred_at=datetime(2026, 9, 15, 8, 0, tzinfo=UTC)),
        )

        weeks = {week.week_start: week.xp for week in self._read().weekly_xp}

        assert weeks[date(2026, 9, 7)] == 25
        assert weeks[CURRENT_WEEK_START] == 7
        assert sum(weeks.values()) == 32

    def test_should_exclude_grants_older_than_the_twelve_week_window(self) -> None:
        self._given_grants(
            self._grant(40, occurred_at=datetime(2026, 6, 28, 23, 0, tzinfo=UTC)),
            self._grant(3, occurred_at=datetime(2026, 6, 29, 0, 0, tzinfo=UTC)),
        )

        weeks = self._read().weekly_xp

        assert weeks[0].week_start == FIRST_WEEK_START
        assert weeks[0].xp == 3
        assert sum(week.xp for week in weeks) == 3

    def test_should_split_grants_across_the_sunday_monday_local_boundary(self) -> None:
        self._given_grants(
            self._grant(10, occurred_at=datetime(2026, 9, 14, 2, 30, tzinfo=UTC)),
            self._grant(4, occurred_at=datetime(2026, 9, 14, 3, 30, tzinfo=UTC)),
        )

        weeks = {
            week.week_start: week.xp
            for week in self._read(time_zone=SAO_PAULO).weekly_xp
        }

        assert weeks[date(2026, 9, 7)] == 10
        assert weeks[CURRENT_WEEK_START] == 4

    def test_should_read_grants_from_the_local_midnight_of_the_first_week(self) -> None:
        self._read(time_zone=SAO_PAULO)

        self.repositories.xp_grants.find_many_by_account_id_occurred_since.assert_called_once_with(
            ACCOUNT_ID, datetime(2026, 6, 29, tzinfo=ZoneInfo(SAO_PAULO))
        )

    @pytest.mark.parametrize('time_zone', [None, '', 'Not/AZone'])
    def test_should_group_grants_in_utc_for_an_unusable_time_zone(
        self, time_zone: str | None
    ) -> None:
        self._given_grants(
            self._grant(10, occurred_at=datetime(2026, 9, 14, 2, 30, tzinfo=UTC)),
        )

        weeks = {
            week.week_start: week.xp
            for week in self._read(time_zone=time_zone).weekly_xp
        }

        assert weeks[CURRENT_WEEK_START] == 10
        assert weeks[date(2026, 9, 7)] == 0
        self.repositories.xp_grants.find_many_by_account_id_occurred_since.assert_called_once_with(
            ACCOUNT_ID, datetime(2026, 6, 29, tzinfo=UTC)
        )

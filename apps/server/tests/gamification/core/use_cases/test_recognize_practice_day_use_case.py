from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import RecognizePracticeDayUseCase
from shifu.shared.core.interfaces import IdentifierProvider

ACCOUNT_ID = 'account-1'
SAO_PAULO = 'America/Sao_Paulo'
TOKYO = 'Asia/Tokyo'


class TestRecognizePracticeDayUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = 'practice-day-1'
        self.profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID, created_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
        self.repositories.profiles.find_by_account_id.return_value = self.profile
        self.repositories.practice_days.try_add.return_value = True
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = ()
        self.subject = RecognizePracticeDayUseCase(self.database, self.identifiers)

    def _recognize(
        self,
        *,
        practiced_at: datetime,
        time_zone: str | None,
        now: datetime | None = None,
    ) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            practiced_at=practiced_at,
            time_zone=time_zone,
            now=now or practiced_at,
        )

    def _stored_streak(self) -> PracticeStreak:
        self.repositories.profiles.update.assert_called_once()
        return self.profile.streak

    def test_should_recognize_a_practice_day_for_the_submission_local_date(
        self,
    ) -> None:
        practiced_at = datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 10),
        )

        self._recognize(practiced_at=practiced_at, time_zone=SAO_PAULO)

        self.repositories.practice_days.try_add.assert_called_once()
        stored = self.repositories.practice_days.try_add.call_args.args[0]
        assert stored.practice_date == date(2026, 9, 10)
        assert stored.account_id == ACCOUNT_ID

    def test_should_recognize_practice_even_when_no_xp_was_granted(self) -> None:
        """A score of 0 still counts: practice is independent of reward."""
        practiced_at = datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 10),
        )

        self._recognize(practiced_at=practiced_at, time_zone=SAO_PAULO)

        self.repositories.practice_days.try_add.assert_called_once()
        assert self._stored_streak().current == 1

    def test_should_write_nothing_when_the_account_has_no_profile(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        self._recognize(
            practiced_at=datetime(2026, 9, 10, 15, 0, tzinfo=UTC),
            time_zone=SAO_PAULO,
        )

        self.repositories.practice_days.try_add.assert_not_called()
        self.repositories.profiles.update.assert_not_called()

    def test_should_collapse_a_second_practice_on_an_already_recognized_date(
        self,
    ) -> None:
        self.repositories.practice_days.try_add.return_value = False

        self._recognize(
            practiced_at=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
            time_zone=SAO_PAULO,
        )

        self.repositories.practice_days.find_many_dates_by_account_id.assert_not_called()
        self.repositories.profiles.update.assert_not_called()

    def test_should_date_the_day_in_a_zone_behind_utc(self) -> None:
        """02:30Z on 1 March is still 28 February in Sao Paulo."""
        practiced_at = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 2, 28),
        )

        self._recognize(practiced_at=practiced_at, time_zone=SAO_PAULO)

        stored = self.repositories.practice_days.try_add.call_args.args[0]
        assert stored.practice_date == date(2026, 2, 28)

    def test_should_date_the_day_in_a_zone_ahead_of_utc(self) -> None:
        """22:30Z on 1 March is already 2 March in Tokyo."""
        practiced_at = datetime(2026, 3, 1, 22, 30, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 3, 2),
        )

        self._recognize(practiced_at=practiced_at, time_zone=TOKYO)

        stored = self.repositories.practice_days.try_add.call_args.args[0]
        assert stored.practice_date == date(2026, 3, 2)

    def test_should_freeze_the_submission_zone_on_the_stored_day(self) -> None:
        practiced_at = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 2, 28),
        )

        self._recognize(practiced_at=practiced_at, time_zone=SAO_PAULO)

        stored = self.repositories.practice_days.try_add.call_args.args[0]
        assert stored.time_zone == SAO_PAULO
        assert stored.practiced_at == practiced_at

    @pytest.mark.parametrize('time_zone', [None, '', 'Mars/Olympus'])
    def test_should_fall_back_to_utc_instead_of_dropping_the_day(
        self, time_zone: str | None
    ) -> None:
        """An unusable zone must never cost the learner a practice day."""
        practiced_at = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 3, 1),
        )

        self._recognize(practiced_at=practiced_at, time_zone=time_zone)

        self.repositories.practice_days.try_add.assert_called_once()
        stored = self.repositories.practice_days.try_add.call_args.args[0]
        assert stored.time_zone == 'UTC'
        assert stored.practice_date == date(2026, 3, 1)

    def test_should_resolve_midnight_boundaries_within_the_local_zone(self) -> None:
        """03:00Z is local midnight in Sao Paulo; 02:59Z is the previous day."""
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 10),
        )
        self._recognize(
            practiced_at=datetime(2026, 9, 10, 3, 0, tzinfo=UTC),
            time_zone=SAO_PAULO,
            now=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
        )
        assert self.repositories.practice_days.try_add.call_args.args[
            0
        ].practice_date == date(2026, 9, 10)

        self.repositories.practice_days.try_add.reset_mock()
        self._recognize(
            practiced_at=datetime(2026, 9, 10, 2, 59, tzinfo=UTC),
            time_zone=SAO_PAULO,
            now=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
        )
        assert self.repositories.practice_days.try_add.call_args.args[
            0
        ].practice_date == date(2026, 9, 9)

    def test_should_join_two_runs_when_a_late_evaluation_fills_the_gap(self) -> None:
        """D-2 and D exist; recognizing D-1 must produce a run of 3."""
        now = datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 8),
            date(2026, 9, 9),
            date(2026, 9, 10),
        )

        self._recognize(
            practiced_at=datetime(2026, 9, 9, 15, 0, tzinfo=UTC),
            time_zone='UTC',
            now=now,
        )

        streak = self._stored_streak()
        assert streak.current == 3
        assert streak.longest >= 3
        assert streak.latest_practice_date == date(2026, 9, 10)

    def test_should_restart_the_current_streak_at_one_after_a_break(self) -> None:
        now = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 3),
            date(2026, 9, 20),
        )

        self._recognize(
            practiced_at=now,
            time_zone='UTC',
            now=now,
        )

        streak = self._stored_streak()
        assert streak.current == 1
        assert streak.longest == 3

    def test_should_keep_a_streak_held_through_yesterday_active_today(self) -> None:
        now = datetime(2026, 9, 11, 10, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 9),
            date(2026, 9, 10),
        )

        self._recognize(
            practiced_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
            time_zone='UTC',
            now=now,
        )

        assert self._stored_streak().current == 2

    def test_should_keep_the_longest_run_when_it_is_not_the_current_one(self) -> None:
        now = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 3),
            date(2026, 9, 4),
            date(2026, 9, 14),
            date(2026, 9, 15),
        )

        self._recognize(practiced_at=now, time_zone='UTC', now=now)

        streak = self._stored_streak()
        assert streak.longest == 4
        assert streak.current == 2
        assert streak.latest_practice_date == date(2026, 9, 15)

    def test_should_record_a_single_practice_day_as_a_run_of_one(self) -> None:
        now = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 15),
        )

        self._recognize(practiced_at=now, time_zone='UTC', now=now)

        streak = self._stored_streak()
        assert streak.current == 1
        assert streak.longest == 1
        assert streak.latest_practice_date == date(2026, 9, 15)

    def test_should_report_zero_current_when_the_latest_day_is_older(self) -> None:
        now = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 14),
            date(2026, 9, 15),
        )

        self._recognize(
            practiced_at=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
            time_zone='UTC',
            now=now,
        )

        streak = self._stored_streak()
        assert streak.current == 0
        assert streak.longest == 2

    def test_should_stamp_the_recognition_and_profile_update_with_now(self) -> None:
        now = datetime(2026, 9, 16, 9, 30, tzinfo=UTC)
        practiced_at = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 15),
        )

        self._recognize(practiced_at=practiced_at, time_zone='UTC', now=now)

        stored = self.repositories.practice_days.try_add.call_args.args[0]
        assert stored.recognized_at == now
        assert stored.practiced_at == practiced_at
        assert stored.id == 'practice-day-1'
        self.repositories.profiles.update.assert_called_once_with(self.profile)
        assert self.profile.updated_at == now

    def test_should_evaluate_today_in_the_recognized_days_zone(self) -> None:
        """23:00Z on 15 September is already 16 September in Tokyo, so a run
        ending on the 15th is still current rather than broken."""
        now = datetime(2026, 9, 15, 23, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 14),
            date(2026, 9, 15),
        )

        self._recognize(
            practiced_at=datetime(2026, 9, 15, 10, 0, tzinfo=UTC),
            time_zone=TOKYO,
            now=now,
        )

        assert self._stored_streak().current == 2

    def test_should_scope_every_lookup_to_the_recognized_account(self) -> None:
        now = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 15),
        )

        self._recognize(practiced_at=now, time_zone='UTC', now=now)

        self.repositories.profiles.find_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.practice_days.find_many_dates_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )

    def test_should_not_inflate_a_run_that_follows_a_gap(self) -> None:
        now = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            date(2026, 9, 1),
            date(2026, 9, 3),
            date(2026, 9, 4),
        )

        self._recognize(
            practiced_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
            time_zone='UTC',
            now=now,
        )

        assert self._stored_streak().longest == 2

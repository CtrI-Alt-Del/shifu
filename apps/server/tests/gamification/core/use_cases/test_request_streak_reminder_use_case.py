from datetime import UTC, date, datetime, timedelta
from unittest.mock import create_autospec
from zoneinfo import ZoneInfo

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.events import (
    StreakReminderRequestedEvent,
    StreakReminderRequestedPayload,
)
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import RequestStreakReminderUseCase
from shifu.shared.core.domain.structures import ActiveAccount
from shifu.shared.core.interfaces import ActiveAccountProvider

ACCOUNT_ID = 'account-1'
SAO_PAULO = 'America/Sao_Paulo'
KOLKATA = 'Asia/Kolkata'
KATHMANDU = 'Asia/Kathmandu'
NEW_YORK = 'America/New_York'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
TODAY = date(2026, 9, 15)
YESTERDAY = date(2026, 9, 14)
# 18:00 on 15 September in America/Sao_Paulo (UTC-03:00).
SLOT = datetime(2026, 9, 15, 21, 0, tzinfo=UTC)


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _days_ending(last: date, count: int) -> tuple[date, ...]:
    return tuple(last - timedelta(days=offset) for offset in reversed(range(count)))


class TestRequestStreakReminderUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(ActiveAccountProvider, instance=True)
        self.subject = RequestStreakReminderUseCase(self.database, self.provider)
        self._given_account(SAO_PAULO)
        self._given_profile()
        self._given_practice_days(YESTERDAY)

    def _given_account(self, time_zone: str | None, *, active: bool = True) -> None:
        self.provider.find_many_active.return_value = (
            (ActiveAccount(account_id=ACCOUNT_ID, time_zone=time_zone),)
            if active
            else ()
        )

    def _given_profile(self, *, hour: int = 18) -> GamificationProfile:
        self.profile = GamificationProfileFaker.fake(
            account_id=ACCOUNT_ID,
            total_xp=240,
            streak=PracticeStreak(current=1, longest=3, latest_practice_date=YESTERDAY),
            reminder_hour=hour,
            created_at=CREATED_AT,
        )
        self.repositories.profiles.find_by_account_id.return_value = self.profile
        return self.profile

    def _given_practice_days(self, *days: date) -> None:
        self.repositories.practice_days.find_many_dates_by_account_id.return_value = (
            days
        )

    def _recorded_events(self) -> list[StreakReminderRequestedEvent]:
        return [call.args[0] for call in self.repositories.events.add.call_args_list]

    def _assert_no_request(self) -> None:
        self.repositories.events.add.assert_not_called()

    def test_should_request_the_reminder_for_a_streak_through_yesterday(self) -> None:
        requested = self.subject.execute(ACCOUNT_ID, slot_start=SLOT)

        assert requested is True
        assert self._recorded_events() == [
            StreakReminderRequestedEvent(
                payload=StreakReminderRequestedPayload(
                    account_id=ACCOUNT_ID,
                    local_date='2026-09-15',
                    streak_days=1,
                    expires_at='2026-09-16T03:00:00Z',
                )
            )
        ]
        assert (
            self._recorded_events()[0].name == 'gamification/streak-reminder.requested'
        )
        self.provider.find_many_active.assert_called_once_with([ACCOUNT_ID])

    def test_should_carry_the_length_of_the_current_run_as_the_streak(self) -> None:
        self._given_practice_days(
            date(2026, 9, 1), date(2026, 9, 2), *_days_ending(YESTERDAY, 5)
        )

        self.subject.execute(ACCOUNT_ID, slot_start=SLOT)

        assert self._recorded_events()[0].payload.streak_days == 5

    def test_should_not_request_when_the_learner_has_no_streak(self) -> None:
        self._given_practice_days()

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()

    def test_should_not_request_when_the_streak_was_broken_before_yesterday(
        self,
    ) -> None:
        self._given_practice_days(*_days_ending(date(2026, 9, 13), 4))

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()

    def test_should_not_request_when_practice_was_already_recognized_today(
        self,
    ) -> None:
        self._given_practice_days(YESTERDAY, TODAY)

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()

    def test_should_not_request_when_only_today_was_practiced(self) -> None:
        self._given_practice_days(TODAY)

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()

    def test_should_request_while_an_evaluation_is_still_pending_today(self) -> None:
        # A submission waiting for its evaluation has not produced a practice
        # day yet, so the recognized dates still end yesterday.
        self._given_practice_days(*_days_ending(YESTERDAY, 2))

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is True
        assert self._recorded_events()[0].payload.streak_days == 2

    def test_should_not_request_when_the_account_is_no_longer_active(self) -> None:
        self._given_account(SAO_PAULO, active=False)

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()
        self.repositories.profiles.find_by_account_id.assert_not_called()

    def test_should_not_request_when_the_profile_does_not_exist(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()

    def test_should_not_request_when_the_hour_no_longer_matches(self) -> None:
        self._given_profile(hour=19)

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        self._assert_no_request()

    @pytest.mark.parametrize('minutes', [-15, 15, 30, 45])
    def test_should_not_request_in_the_neighbouring_slots_of_the_hour(
        self, minutes: int
    ) -> None:
        slot = SLOT + timedelta(minutes=minutes)

        assert self.subject.execute(ACCOUNT_ID, slot_start=slot) is False
        self._assert_no_request()

    def test_should_skip_only_the_hour_check_when_asked_to_ignore_the_hour(
        self,
    ) -> None:
        self._given_profile(hour=7)

        requested = self.subject.execute(ACCOUNT_ID, slot_start=SLOT, ignore_hour=True)

        assert requested is True
        assert len(self._recorded_events()) == 1

    def test_should_keep_every_other_rule_when_the_hour_is_ignored(self) -> None:
        self._given_practice_days(YESTERDAY, TODAY)
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=SLOT, ignore_hour=True) is False
        )

        self._given_practice_days()
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=SLOT, ignore_hour=True) is False
        )

        self._given_practice_days(YESTERDAY)
        self._given_account(SAO_PAULO, active=False)
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=SLOT, ignore_hour=True) is False
        )

        self._assert_no_request()

    @pytest.mark.parametrize(
        ('time_zone', 'hour', 'slot', 'expected_expires_at'),
        [
            (SAO_PAULO, 18, _utc(2026, 9, 15, 21, 0), '2026-09-16T03:00:00Z'),
            (SAO_PAULO, 6, _utc(2026, 9, 15, 9, 0), '2026-09-16T03:00:00Z'),
            (SAO_PAULO, 22, _utc(2026, 9, 16, 1, 0), '2026-09-16T03:00:00Z'),
            (KOLKATA, 18, _utc(2026, 9, 15, 12, 30), '2026-09-15T18:30:00Z'),
            (KOLKATA, 6, _utc(2026, 9, 15, 0, 30), '2026-09-15T18:30:00Z'),
            (KATHMANDU, 22, _utc(2026, 9, 15, 16, 15), '2026-09-15T18:15:00Z'),
            (KATHMANDU, 6, _utc(2026, 9, 15, 0, 15), '2026-09-15T18:15:00Z'),
            ('UTC', 18, _utc(2026, 9, 15, 18, 0), '2026-09-16T00:00:00Z'),
        ],
    )
    def test_should_use_the_exact_local_hour_and_end_the_local_day_in_utc(
        self, time_zone: str, hour: int, slot: datetime, expected_expires_at: str
    ) -> None:
        self._given_account(time_zone)
        self._given_profile(hour=hour)

        requested = self.subject.execute(ACCOUNT_ID, slot_start=slot)

        assert requested is True
        event = self._recorded_events()[0]
        assert event.payload.local_date == '2026-09-15'
        assert event.payload.expires_at == expected_expires_at
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=slot - timedelta(minutes=15))
            is False
        )
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=slot + timedelta(minutes=15))
            is False
        )
        assert len(self._recorded_events()) == 1

    @pytest.mark.parametrize(
        ('local_date', 'slot', 'expected_expires_at'),
        [
            # Ordinary winter day: the day ends at 00:00 EST, 05:00 UTC.
            (date(2026, 1, 15), _utc(2026, 1, 15, 23, 0), '2026-01-16T05:00:00Z'),
            # Spring forward: 8 March has 23 hours and ends at 00:00 EDT.
            (date(2026, 3, 7), _utc(2026, 3, 7, 23, 0), '2026-03-08T05:00:00Z'),
            (date(2026, 3, 8), _utc(2026, 3, 8, 22, 0), '2026-03-09T04:00:00Z'),
            # Fall back: 1 November has 25 hours and ends at 00:00 EST.
            (date(2026, 10, 31), _utc(2026, 10, 31, 22, 0), '2026-11-01T04:00:00Z'),
            (date(2026, 11, 1), _utc(2026, 11, 1, 23, 0), '2026-11-02T05:00:00Z'),
        ],
    )
    def test_should_end_the_local_day_at_the_right_instant_across_dst(
        self, local_date: date, slot: datetime, expected_expires_at: str
    ) -> None:
        self._given_account(NEW_YORK)
        self._given_practice_days(local_date - timedelta(days=1))

        requested = self.subject.execute(ACCOUNT_ID, slot_start=slot)

        assert requested is True
        event = self._recorded_events()[0]
        assert event.payload.local_date == local_date.isoformat()
        assert event.payload.expires_at == expected_expires_at

    @pytest.mark.parametrize('time_zone', [None, '', 'Mars/Olympus_Mons'])
    def test_should_fall_back_to_utc_when_the_zone_is_missing_or_invalid(
        self, time_zone: str | None
    ) -> None:
        self._given_account(time_zone)

        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=_utc(2026, 9, 15, 21, 0))
            is False
        )
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=_utc(2026, 9, 15, 18, 0))
            is True
        )

        event = self._recorded_events()[0]
        assert event.payload.local_date == '2026-09-15'
        assert event.payload.expires_at == '2026-09-16T00:00:00Z'

    def test_should_use_the_current_time_zone_with_the_same_hour(self) -> None:
        self._given_account('Asia/Tokyo')

        assert self.subject.execute(ACCOUNT_ID, slot_start=SLOT) is False
        assert (
            self.subject.execute(ACCOUNT_ID, slot_start=_utc(2026, 9, 15, 9, 0)) is True
        )

        assert self._recorded_events()[0].payload.local_date == '2026-09-15'

    def test_should_give_the_same_result_when_the_same_slot_is_retried(self) -> None:
        first = self.subject.execute(ACCOUNT_ID, slot_start=SLOT)
        second = self.subject.execute(ACCOUNT_ID, slot_start=SLOT)

        assert (first, second) == (True, True)
        first_event, second_event = self._recorded_events()
        assert first_event == second_event

    def test_should_change_no_state_and_grant_no_xp(self) -> None:
        before = GamificationProfileFaker.fake(
            id=self.profile.id,
            account_id=ACCOUNT_ID,
            total_xp=240,
            streak=PracticeStreak(current=1, longest=3, latest_practice_date=YESTERDAY),
            created_at=CREATED_AT,
        )

        self.subject.execute(ACCOUNT_ID, slot_start=SLOT)

        assert self.profile.total_xp == before.total_xp
        assert self.profile.level == before.level
        assert self.profile.streak == before.streak
        assert self.profile.reminder_hour == before.reminder_hour
        assert self.profile.reminder_invite_answered_at is None
        assert self.profile.updated_at == before.updated_at
        self.repositories.profiles.update.assert_not_called()
        self.repositories.profiles.add.assert_not_called()
        self.repositories.xp_grants.add.assert_not_called()
        self.repositories.earned_achievements.try_add.assert_not_called()
        self.repositories.rewarded_milestones.try_add.assert_not_called()
        self.repositories.practice_days.try_add.assert_not_called()
        self.repositories.activity_xp_balances.add.assert_not_called()
        self.repositories.activity_xp_recognitions.try_add.assert_not_called()

    @pytest.mark.parametrize(
        'slot',
        [
            datetime(2026, 9, 15, 21, 0),
            datetime(2026, 9, 15, 21, 7, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 0, 30, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 10, tzinfo=ZoneInfo('Asia/Kolkata')),
        ],
    )
    def test_should_reject_a_slot_that_is_naive_or_not_aligned_without_effects(
        self, slot: datetime
    ) -> None:
        with pytest.raises(InvalidGamificationError):
            self.subject.execute(ACCOUNT_ID, slot_start=slot)

        self.provider.find_many_active.assert_not_called()
        self.database.transaction.assert_not_called()
        self._assert_no_request()

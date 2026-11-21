from datetime import UTC, date, datetime, timedelta
from unittest.mock import create_autospec
from zoneinfo import ZoneInfo

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.events import (
    StreakReminderDueEvent,
    StreakReminderDuePayload,
)
from shifu.gamification.core.domain.structures import (
    PracticeStreak,
    StreakReminderFanOutPage,
)
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import FanOutDueStreakRemindersUseCase
from shifu.shared.core.domain.structures import ActiveAccount
from shifu.shared.core.interfaces import ActiveAccountProvider

SAO_PAULO = 'America/Sao_Paulo'
KOLKATA = 'Asia/Kolkata'
KATHMANDU = 'Asia/Kathmandu'
NEW_YORK = 'America/New_York'
SLOT_STEP = timedelta(minutes=15)
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
SLOT = datetime(2026, 9, 15, 21, 0, tzinfo=UTC)


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


class TestFanOutDueStreakRemindersUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.repositories.profiles.find_many_reminder_candidates.return_value = ()
        self.provider = create_autospec(ActiveAccountProvider, instance=True)
        self.provider.find_many_active.return_value = ()
        self.candidates: list[GamificationProfile] = []
        self.accounts: list[ActiveAccount] = []
        self.subject = FanOutDueStreakRemindersUseCase(self.database, self.provider)

    def _given_candidate(
        self,
        account_id: str,
        *,
        hour: int = 18,
        time_zone: str | None = SAO_PAULO,
        active: bool = True,
    ) -> GamificationProfile:
        profile = GamificationProfileFaker.fake(
            account_id=account_id,
            streak=PracticeStreak(
                current=3, longest=3, latest_practice_date=date(2026, 9, 14)
            ),
            reminder_hour=hour,
            created_at=CREATED_AT,
        )
        self.candidates.append(profile)
        if active:
            self.accounts.append(
                ActiveAccount(account_id=account_id, time_zone=time_zone)
            )
        self._publish()
        return profile

    def _publish(self) -> None:
        self.repositories.profiles.find_many_reminder_candidates.return_value = tuple(
            self.candidates
        )
        self.provider.find_many_active.return_value = tuple(self.accounts)

    def _recorded_events(self) -> list[StreakReminderDueEvent]:
        return [call.args[0] for call in self.repositories.events.add.call_args_list]

    def _due_account_ids(self, slot: datetime) -> list[str]:
        self.repositories.events.add.reset_mock()
        self.subject.execute(slot)
        return [event.payload.account_id for event in self._recorded_events()]

    def _due_slots(
        self, start: datetime, *, days: int = 1
    ) -> list[tuple[datetime, StreakReminderDueEvent]]:
        due: list[tuple[datetime, StreakReminderDueEvent]] = []
        for index in range(days * 96):
            slot = start + index * SLOT_STEP
            self.repositories.events.add.reset_mock()
            self.subject.execute(slot)
            due.extend((slot, event) for event in self._recorded_events())
        return due

    @pytest.mark.parametrize(
        ('time_zone', 'hour', 'expected_slot'),
        [
            (SAO_PAULO, 18, _utc(2026, 9, 15, 21, 0)),
            (SAO_PAULO, 6, _utc(2026, 9, 15, 9, 0)),
            (SAO_PAULO, 22, _utc(2026, 9, 15, 1, 0)),
            (KOLKATA, 18, _utc(2026, 9, 15, 12, 30)),
            (KOLKATA, 6, _utc(2026, 9, 15, 0, 30)),
            (KOLKATA, 22, _utc(2026, 9, 15, 16, 30)),
            (KATHMANDU, 18, _utc(2026, 9, 15, 12, 15)),
            (KATHMANDU, 6, _utc(2026, 9, 15, 0, 15)),
            (KATHMANDU, 22, _utc(2026, 9, 15, 16, 15)),
        ],
    )
    def test_should_be_due_only_in_the_slot_that_starts_at_the_local_hour(
        self, time_zone: str, hour: int, expected_slot: datetime
    ) -> None:
        self._given_candidate('account-1', hour=hour, time_zone=time_zone)

        due = self._due_slots(_utc(2026, 9, 15, 0, 0), days=1)

        assert [slot for slot, _ in due] == [expected_slot]

    @pytest.mark.parametrize(
        ('time_zone', 'hour', 'expected_slot', 'local_date'),
        [
            (SAO_PAULO, 22, _utc(2026, 9, 16, 1, 0), '2026-09-15'),
            (KOLKATA, 6, _utc(2026, 9, 15, 0, 30), '2026-09-15'),
            (KATHMANDU, 22, _utc(2026, 9, 15, 16, 15), '2026-09-15'),
        ],
    )
    def test_should_not_be_due_fifteen_minutes_before_or_after_the_boundary(
        self,
        time_zone: str,
        hour: int,
        expected_slot: datetime,
        local_date: str,
    ) -> None:
        self._given_candidate('account-1', hour=hour, time_zone=time_zone)

        assert self._due_account_ids(expected_slot - SLOT_STEP) == []
        assert self._due_account_ids(expected_slot) == ['account-1']
        assert self._due_account_ids(expected_slot + SLOT_STEP) == []
        assert self._recorded_events() == []
        self.repositories.events.add.reset_mock()
        self.subject.execute(expected_slot)
        assert self._recorded_events()[0].payload.local_date == local_date

    def test_should_record_one_due_event_with_the_local_date_and_the_slot(self) -> None:
        self._given_candidate('account-1', hour=18, time_zone=SAO_PAULO)

        page = self.subject.execute(SLOT)

        assert self._recorded_events() == [
            StreakReminderDueEvent(
                payload=StreakReminderDuePayload(
                    account_id='account-1',
                    local_date='2026-09-15',
                    slot_start='2026-09-15T21:00:00Z',
                )
            )
        ]
        assert self._recorded_events()[0].name == 'gamification/streak-reminder.due'
        assert page == StreakReminderFanOutPage(due_count=1, next_cursor=None)

    def test_should_use_the_local_date_of_the_zone_when_it_differs_from_utc(
        self,
    ) -> None:
        self._given_candidate('account-1', hour=6, time_zone='Pacific/Auckland')

        # 06:00 on 16 September in Auckland (UTC+12) is 18:00 UTC on the 15th.
        self.subject.execute(_utc(2026, 9, 15, 18, 0))

        event = self._recorded_events()[0]
        assert event.payload.local_date == '2026-09-16'
        assert event.payload.slot_start == '2026-09-15T18:00:00Z'

    def test_should_give_the_same_result_when_the_same_slot_runs_again(self) -> None:
        self._given_candidate('account-1', hour=18, time_zone=SAO_PAULO)
        self._given_candidate('account-2', hour=18, time_zone=KOLKATA)
        self._given_candidate('account-3', hour=19, time_zone=SAO_PAULO)

        first_page = self.subject.execute(SLOT)
        first_events = self._recorded_events()
        self.repositories.events.add.reset_mock()
        second_page = self.subject.execute(SLOT)

        assert [event.payload.account_id for event in first_events] == ['account-1']
        assert self._recorded_events() == first_events
        assert second_page == first_page

    def test_should_keep_the_same_hour_when_the_time_zone_changes(self) -> None:
        self._given_candidate('account-1', hour=18, time_zone=SAO_PAULO)
        assert self._due_account_ids(_utc(2026, 9, 15, 21, 0)) == ['account-1']

        self.accounts[:] = [
            ActiveAccount(account_id='account-1', time_zone='Asia/Tokyo')
        ]
        self._publish()

        assert self._due_account_ids(_utc(2026, 9, 15, 21, 0)) == []
        assert self._due_account_ids(_utc(2026, 9, 15, 9, 0)) == ['account-1']

    def test_should_apply_a_new_hour_the_same_day_only_while_its_slot_has_not_started(
        self,
    ) -> None:
        # Local 19:00 on 15 September in Sao Paulo is 22:00 UTC. The first
        # learner moved from 20 to 19 at 18:50; the second moved from 18 to 19
        # at 19:10, after the 19:00 slot had already run with hour 18.
        self._given_candidate('account-early', hour=19)
        self._given_candidate('account-late', hour=18)
        slot_at_19 = _utc(2026, 9, 15, 22, 0)

        assert self._due_account_ids(slot_at_19) == ['account-early']

        self.candidates[1] = GamificationProfileFaker.fake(
            account_id='account-late',
            streak=self.candidates[1].streak,
            reminder_hour=19,
            created_at=CREATED_AT,
        )
        self._publish()
        for minutes in (15, 30, 45, 60):
            later_slot = slot_at_19 + timedelta(minutes=minutes)
            assert 'account-late' not in self._due_account_ids(later_slot)
        assert self._due_account_ids(slot_at_19 + timedelta(days=1)) == [
            'account-early',
            'account-late',
        ]

    @pytest.mark.parametrize(
        ('slot', 'local_date'),
        [
            (_utc(2026, 3, 7, 23, 0), '2026-03-07'),
            (_utc(2026, 3, 8, 22, 0), '2026-03-08'),
            (_utc(2026, 10, 31, 22, 0), '2026-10-31'),
            (_utc(2026, 11, 1, 23, 0), '2026-11-01'),
        ],
    )
    def test_should_follow_the_offset_in_effect_on_each_day_across_dst(
        self, slot: datetime, local_date: str
    ) -> None:
        self._given_candidate('account-1', hour=18, time_zone=NEW_YORK)

        self.subject.execute(slot)

        assert [event.payload.local_date for event in self._recorded_events()] == [
            local_date
        ]
        self.repositories.events.add.reset_mock()
        self.subject.execute(slot + timedelta(hours=1))
        assert self._recorded_events() == []

    @pytest.mark.parametrize('time_zone', [None, '', 'Mars/Olympus_Mons', 'UTC'])
    def test_should_fall_back_to_utc_when_the_zone_is_missing_or_invalid(
        self, time_zone: str | None
    ) -> None:
        self._given_candidate('account-1', hour=18, time_zone=time_zone)

        assert self._due_account_ids(_utc(2026, 9, 15, 17, 45)) == []
        assert self._due_account_ids(_utc(2026, 9, 15, 18, 0)) == ['account-1']
        assert self._due_account_ids(_utc(2026, 9, 15, 18, 15)) == []

    def test_should_skip_accounts_that_are_not_active(self) -> None:
        self._given_candidate('account-1', hour=18, time_zone=SAO_PAULO)
        self._given_candidate('account-2', hour=18, time_zone=SAO_PAULO, active=False)

        page = self.subject.execute(SLOT)

        assert [event.payload.account_id for event in self._recorded_events()] == [
            'account-1'
        ]
        assert page.due_count == 1

    def test_should_record_nothing_when_every_candidate_is_inactive(self) -> None:
        self._given_candidate('account-1', hour=18, active=False)

        page = self.subject.execute(SLOT)

        assert page == StreakReminderFanOutPage(due_count=0, next_cursor=None)
        self.repositories.events.add.assert_not_called()

    def test_should_ask_for_candidates_from_two_days_before_the_slot_date(
        self,
    ) -> None:
        self.subject.execute(_utc(2026, 9, 15, 0, 0))

        self.repositories.profiles.find_many_reminder_candidates.assert_called_once_with(
            practiced_since=date(2026, 9, 13),
            after_account_id=None,
            limit=FanOutDueStreakRemindersUseCase.PAGE_SIZE,
        )

    def test_should_derive_the_candidate_date_from_the_utc_instant(self) -> None:
        local_slot = datetime(2026, 9, 15, 22, 0, tzinfo=ZoneInfo(SAO_PAULO))

        self.subject.execute(local_slot)

        assert (
            self.repositories.profiles.find_many_reminder_candidates.call_args.kwargs[
                'practiced_since'
            ]
            == date(2026, 9, 14)
        )

    def test_should_accept_an_aligned_slot_expressed_in_another_offset(self) -> None:
        self._given_candidate('account-1', hour=18, time_zone=KOLKATA)

        self.subject.execute(datetime(2026, 9, 15, 18, 0, tzinfo=ZoneInfo(KOLKATA)))

        assert [event.payload.slot_start for event in self._recorded_events()] == [
            '2026-09-15T12:30:00Z'
        ]

    def test_should_resolve_every_active_account_of_a_page_in_one_lookup(
        self,
    ) -> None:
        self._given_candidate('account-1')
        self._given_candidate('account-2')
        self._given_candidate('account-3', active=False)

        self.subject.execute(SLOT)

        self.provider.find_many_active.assert_called_once_with(
            ['account-1', 'account-2', 'account-3']
        )

    def test_should_pass_the_cursor_to_the_candidate_query(self) -> None:
        self.subject.execute(SLOT, after_account_id='account-5')

        self.repositories.profiles.find_many_reminder_candidates.assert_called_once_with(
            practiced_since=date(2026, 9, 13),
            after_account_id='account-5',
            limit=FanOutDueStreakRemindersUseCase.PAGE_SIZE,
        )

    def test_should_return_the_last_account_as_cursor_when_the_page_is_full(
        self,
    ) -> None:
        for index in range(FanOutDueStreakRemindersUseCase.PAGE_SIZE):
            self._given_candidate(f'account-{index:04d}', hour=19)

        page = self.subject.execute(SLOT)

        assert page == StreakReminderFanOutPage(
            due_count=0,
            next_cursor=f'account-{FanOutDueStreakRemindersUseCase.PAGE_SIZE - 1:04d}',
        )

    def test_should_end_the_walk_when_the_page_is_not_full(self) -> None:
        for index in range(FanOutDueStreakRemindersUseCase.PAGE_SIZE - 1):
            self._given_candidate(f'account-{index:04d}', hour=19)

        page = self.subject.execute(SLOT)

        assert page.next_cursor is None

    def test_should_end_the_walk_without_a_lookup_when_no_candidate_remains(
        self,
    ) -> None:
        page = self.subject.execute(SLOT, after_account_id='account-9')

        assert page == StreakReminderFanOutPage(due_count=0, next_cursor=None)
        self.provider.find_many_active.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize(
        'slot',
        [
            datetime(2026, 9, 15, 21, 0),
            datetime(2026, 9, 15, 21, 7, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 1, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 14, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 0, 30, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 0, 0, 1, tzinfo=UTC),
            datetime(2026, 9, 15, 21, 10, tzinfo=ZoneInfo('Asia/Kolkata')),
        ],
    )
    def test_should_reject_a_slot_that_is_naive_or_not_aligned_without_effects(
        self, slot: datetime
    ) -> None:
        with pytest.raises(InvalidGamificationError):
            self.subject.execute(slot)

        self.database.transaction.assert_not_called()
        self.provider.find_many_active.assert_not_called()
        self.repositories.events.add.assert_not_called()

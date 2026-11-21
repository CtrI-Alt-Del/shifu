"""Real-runtime coverage for the streak reminder fan-out (CA-02, CA-03, CA-06).

The cron function is invoked with an explicit aligned `slot_start`, which the
job's `resolve_slot` step honors before the scheduled timestamp. Every seeded
profile practiced on 14 September 2026, so only slots on 15 September can
select it; a real cron firing during the test evaluates the current date,
finds the profiles stale and cannot add rows for the controlled slots. The
assertions also filter the outbox by the controlled `slot_start`.
"""

from collections import Counter
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, select

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.fakers.identity.entities import AccountFaker
from shifu.gamification.core.domain.events import StreakReminderDueEvent
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

_FUNCTION_ID = 'shifu-gamification-fan-out-due-streak-reminders'
_NOW = datetime(2026, 9, 1, tzinfo=UTC)
_PRACTICE_STREAK = PracticeStreak(
    current=3, longest=3, latest_practice_date=date(2026, 9, 14)
)
_STALE_STREAK = PracticeStreak(
    current=0, longest=3, latest_practice_date=date(2026, 9, 10)
)

# 18:00 in America/Sao_Paulo and America/Argentina/Buenos_Aires (UTC-03:00),
# and 17:00 in America/New_York (UTC-04:00 in September).
_SLOT = '2026-09-15T21:00:00Z'
# 18:00 in Asia/Tokyo (UTC+09:00).
_TOKYO_SLOT = '2026-09-15T09:00:00Z'
# 18:00 in Asia/Kolkata (UTC+05:30) and its neighbouring slots.
_KOLKATA_SLOT = '2026-09-15T12:30:00Z'
_BEFORE_KOLKATA_SLOT = '2026-09-15T12:15:00Z'
_AFTER_KOLKATA_SLOT = '2026-09-15T12:45:00Z'
# 06:00 in Asia/Kathmandu (UTC+05:45).
_KATHMANDU_SLOT = '2026-09-15T00:15:00Z'

# Filler ids sort before every scenario id, so the scenario accounts land on
# the second candidate page.
_FILLER_PREFIX = '01SHFA'
_SCENARIO_PREFIX = '01SHFZ'


def _account_id(label: str) -> str:
    return f'{_SCENARIO_PREFIX}{label:0>20}'[:26]


def _seed_scenario(fixture: 'InngestFixture', *, filler_profiles: int = 0) -> None:
    """Seed Identity accounts and Gamification profiles for every scenario."""
    ids = SystemIdentifierProvider()
    # label, hour, zone, status, streak
    scenarios: list[tuple[str, int, str, AccountStatus, PracticeStreak]] = [
        ('SAOPAULO', 18, 'America/Sao_Paulo', AccountStatus.ACTIVE, _PRACTICE_STREAK),
        (
            'BUENOSAIRES',
            18,
            'America/Argentina/Buenos_Aires',
            AccountStatus.ACTIVE,
            _PRACTICE_STREAK,
        ),
        ('NEWYORK', 17, 'America/New_York', AccountStatus.ACTIVE, _PRACTICE_STREAK),
        ('NEWYORKLATE', 18, 'America/New_York', AccountStatus.ACTIVE, _PRACTICE_STREAK),
        (
            'SAOPAULOHOUR19',
            19,
            'America/Sao_Paulo',
            AccountStatus.ACTIVE,
            _PRACTICE_STREAK,
        ),
        (
            'PENDING',
            18,
            'America/Sao_Paulo',
            AccountStatus.PENDING_CONFIRMATION,
            _PRACTICE_STREAK,
        ),
        ('DELETED', 18, 'America/Sao_Paulo', AccountStatus.DELETED, _PRACTICE_STREAK),
        ('STALE', 18, 'America/Sao_Paulo', AccountStatus.ACTIVE, _STALE_STREAK),
        ('KOLKATA', 18, 'Asia/Kolkata', AccountStatus.ACTIVE, _PRACTICE_STREAK),
        ('KATHMANDU', 6, 'Asia/Kathmandu', AccountStatus.ACTIVE, _PRACTICE_STREAK),
        (
            'TIMEZONECHANGE',
            18,
            'America/Sao_Paulo',
            AccountStatus.ACTIVE,
            _PRACTICE_STREAK,
        ),
    ]
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        identity_database = SqlalchemyIdentityDatabase(engine, id_provider=ids)
        gamification_database = SqlalchemyGamificationDatabase(engine, id_provider=ids)
        with identity_database.transaction() as repositories:
            for label, _hour, zone, status, _streak in scenarios:
                repositories.accounts.add(
                    AccountFaker.fake(
                        id=_account_id(label),
                        email=f'{label.lower()}@example.com',
                        status=status,
                        time_zone=zone,
                        created_at=_NOW,
                    )
                )
        with gamification_database.transaction() as repositories:
            for label, hour, _zone, _status, streak in scenarios:
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        account_id=_account_id(label),
                        streak=streak,
                        reminder_hour=hour,
                        created_at=_NOW,
                    )
                )
            for index in range(filler_profiles):
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        account_id=f'{_FILLER_PREFIX}{index:020d}',
                        streak=_PRACTICE_STREAK,
                        reminder_hour=18,
                        created_at=_NOW,
                    )
                )
    finally:
        engine.dispose()


def _due_account_ids(session: 'Session', slot_start: str) -> list[str]:
    rows = session.scalars(
        select(EventModel).where(EventModel.name == StreakReminderDueEvent.EVENT_NAME)
    )
    return sorted(
        str(row.payload['account_id'])
        for row in rows
        if row.payload.get('slot_start') == slot_start
    )


def _due_payloads(session: 'Session', slot_start: str) -> dict[str, dict[str, object]]:
    rows = session.scalars(
        select(EventModel).where(EventModel.name == StreakReminderDueEvent.EVENT_NAME)
    )
    return {
        str(row.payload['account_id']): dict(row.payload)
        for row in rows
        if row.payload.get('slot_start') == slot_start
    }


def _invoke(fixture: 'InngestFixture', slot_start: str) -> None:
    fixture.invoke_function(_FUNCTION_ID, {'slot_start': slot_start})


class TestFanOutDueStreakRemindersJob:
    def test_should_record_due_events_only_for_active_accounts_whose_local_hour_matches(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        # More than one page of candidates, so the walk needs a second durable
        # step. The scenario accounts sort after the filler profiles.
        _seed_scenario(inngest_fixture, filler_profiles=201)
        expected = sorted(
            _account_id(label)
            for label in ('SAOPAULO', 'BUENOSAIRES', 'NEWYORK', 'TIMEZONECHANGE')
        )

        _invoke(inngest_fixture, _SLOT)
        inngest_fixture.wait_for_database(
            lambda session: len(_due_account_ids(session, _SLOT)) >= len(expected),
            timeout=120.0,
        )

        with inngest_fixture.inspection_session() as session:
            assert _due_account_ids(session, _SLOT) == expected
            payloads = _due_payloads(session, _SLOT)
        assert payloads[_account_id('SAOPAULO')] == {
            'account_id': _account_id('SAOPAULO'),
            'local_date': '2026-09-15',
            'slot_start': _SLOT,
        }
        assert payloads[_account_id('NEWYORK')]['local_date'] == '2026-09-15'

    def test_should_produce_the_same_set_when_the_same_slot_is_invoked_again(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        _seed_scenario(inngest_fixture)
        expected = sorted(
            _account_id(label)
            for label in ('SAOPAULO', 'BUENOSAIRES', 'NEWYORK', 'TIMEZONECHANGE')
        )

        _invoke(inngest_fixture, _SLOT)
        inngest_fixture.wait_for_database(
            lambda session: len(_due_account_ids(session, _SLOT)) >= len(expected)
        )
        _invoke(inngest_fixture, _SLOT)
        inngest_fixture.wait_for_database(
            lambda session: len(_due_account_ids(session, _SLOT)) >= 2 * len(expected)
        )

        with inngest_fixture.inspection_session() as session:
            counts = Counter(_due_account_ids(session, _SLOT))
        assert counts == Counter(dict.fromkeys(expected, 2))

    def test_should_use_the_same_hour_in_the_new_zone_after_a_time_zone_change(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        _seed_scenario(inngest_fixture)
        account_id = _account_id('TIMEZONECHANGE')
        _invoke(inngest_fixture, _SLOT)
        inngest_fixture.wait_for_database(
            lambda session: account_id in _due_account_ids(session, _SLOT)
        )
        due_before = _due_account_ids_snapshot(inngest_fixture, _SLOT)

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            identity_database = SqlalchemyIdentityDatabase(engine)
            with identity_database.transaction() as repositories:
                repositories.accounts.update(
                    AccountFaker.fake(
                        id=account_id,
                        email='timezonechange@example.com',
                        status=AccountStatus.ACTIVE,
                        time_zone='Asia/Tokyo',
                        created_at=_NOW,
                    )
                )
        finally:
            engine.dispose()

        _invoke(inngest_fixture, _SLOT)
        # The page transaction records every due account together, so the other
        # three accounts reaching their second event means this run finished.
        inngest_fixture.wait_for_database(
            lambda session: (
                len(_due_account_ids(session, _SLOT))
                >= len(due_before) + len(due_before) - 1
            )
        )
        _invoke(inngest_fixture, _TOKYO_SLOT)
        inngest_fixture.wait_for_database(
            lambda session: len(_due_account_ids(session, _TOKYO_SLOT)) >= 1
        )

        with inngest_fixture.inspection_session() as session:
            counts = Counter(_due_account_ids(session, _SLOT))
            tokyo = _due_payloads(session, _TOKYO_SLOT)
        assert counts[account_id] == 1
        assert list(tokyo) == [account_id]
        assert tokyo[account_id]['local_date'] == '2026-09-15'

    def test_should_match_the_slot_that_starts_at_the_local_hour_for_fractional_offsets(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        _seed_scenario(inngest_fixture)

        _invoke(inngest_fixture, _BEFORE_KOLKATA_SLOT)
        _invoke(inngest_fixture, _AFTER_KOLKATA_SLOT)
        _invoke(inngest_fixture, _KOLKATA_SLOT)
        _invoke(inngest_fixture, _KATHMANDU_SLOT)
        inngest_fixture.wait_for_database(
            lambda session: (
                len(_due_account_ids(session, _KOLKATA_SLOT)) >= 1
                and len(_due_account_ids(session, _KATHMANDU_SLOT)) >= 1
            )
        )

        with inngest_fixture.inspection_session() as session:
            assert _due_account_ids(session, _KOLKATA_SLOT) == [_account_id('KOLKATA')]
            assert _due_account_ids(session, _KATHMANDU_SLOT) == [
                _account_id('KATHMANDU')
            ]
            assert _due_account_ids(session, _BEFORE_KOLKATA_SLOT) == []
            assert _due_account_ids(session, _AFTER_KOLKATA_SLOT) == []

    def test_should_not_record_anything_for_a_slot_that_is_not_aligned(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        _seed_scenario(inngest_fixture)
        unaligned = '2026-09-15T21:07:00Z'

        _invoke(inngest_fixture, unaligned)
        _invoke(inngest_fixture, _SLOT)
        inngest_fixture.wait_for_database(
            lambda session: len(_due_account_ids(session, _SLOT)) >= 1
        )

        with inngest_fixture.inspection_session() as session:
            assert _due_account_ids(session, unaligned) == []


def _due_account_ids_snapshot(fixture: 'InngestFixture', slot_start: str) -> list[str]:
    with fixture.inspection_session() as session:
        return _due_account_ids(session, slot_start)

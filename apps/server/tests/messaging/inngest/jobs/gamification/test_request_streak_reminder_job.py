"""Real-runtime coverage for the streak reminder request (CA-05, CA-06, CA-07)."""

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import (
    GamificationProfileFaker,
    PracticeDayFaker,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.core.domain.events import (
    StreakReminderDueEvent,
    StreakReminderDuePayload,
    StreakReminderRequestedEvent,
)
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    GamificationProfileModel,
    PracticeDayModel,
    XpGrantModel,
)
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

_NOW = datetime(2026, 9, 1, tzinfo=UTC)
_TIME_ZONE = 'America/Sao_Paulo'
# 18:00 on 15 September 2026 in America/Sao_Paulo (UTC-03:00).
_SLOT = '2026-09-15T21:00:00Z'
_LOCAL_DATE = date(2026, 9, 15)
_YESTERDAY = date(2026, 9, 14)


def _practice_day(
    account_id: str, day: date, ids: SystemIdentifierProvider
) -> PracticeDay:
    practiced_at = datetime(day.year, day.month, day.day, 15, 0, tzinfo=UTC)
    return PracticeDayFaker.fake(
        id=ids.generate(),
        account_id=account_id,
        time_zone=_TIME_ZONE,
        practiced_at=practiced_at,
        recognized_at=practiced_at,
    )


def _seed(
    fixture: 'InngestFixture',
    *,
    account_id: str,
    status: AccountStatus = AccountStatus.ACTIVE,
    hour: int = 18,
    practice_dates: tuple[date, ...] = (_YESTERDAY,),
) -> None:
    ids = SystemIdentifierProvider()
    latest = practice_dates[-1] if practice_dates else None
    streak = (
        PracticeStreak(
            current=len(practice_dates),
            longest=len(practice_dates),
            latest_practice_date=latest,
        )
        if latest is not None
        else PracticeStreak()
    )
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        with SqlalchemyIdentityDatabase(
            engine, id_provider=ids
        ).transaction() as repositories:
            repositories.accounts.add(
                AccountFaker.fake(
                    id=account_id,
                    email=f'{account_id.lower()}@example.com',
                    status=status,
                    time_zone=_TIME_ZONE,
                    created_at=_NOW,
                )
            )
        gamification_database = SqlalchemyGamificationDatabase(engine, id_provider=ids)
        with gamification_database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=account_id,
                    total_xp=120,
                    streak=streak,
                    reminder_hour=hour,
                    created_at=_NOW,
                )
            )
            for day in practice_dates:
                repositories.practice_days.try_add(_practice_day(account_id, day, ids))
    finally:
        engine.dispose()


def _publish_due(
    fixture: 'InngestFixture', *, account_id: str, slot_start: str = _SLOT
) -> str:
    ids = SystemIdentifierProvider()
    event = StreakReminderDueEvent(
        payload=StreakReminderDuePayload(
            account_id=account_id,
            local_date=_LOCAL_DATE.isoformat(),
            slot_start=slot_start,
        )
    )
    event_id = ids.generate()
    fixture.publish(
        event.name,
        {
            'account_id': event.payload.account_id,
            'local_date': event.payload.local_date,
            'slot_start': event.payload.slot_start,
        },
        event_id=event_id,
    )
    return event_id


def _requested_rows(session: 'Session', account_id: str) -> list[EventModel]:
    rows = session.scalars(
        select(EventModel).where(
            EventModel.name == StreakReminderRequestedEvent.EVENT_NAME
        )
    )
    return [row for row in rows if row.payload.get('account_id') == account_id]


def _count(
    session: 'Session',
    model: type[PracticeDayModel] | type[XpGrantModel],
    account_id: str,
) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(model)
            .where(model.account_id == account_id)
        )
        or 0
    )


class TestRequestStreakReminderJob:
    def test_should_record_one_requested_event_and_change_no_gamification_state(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        account_id = SystemIdentifierProvider().generate()
        _seed(
            inngest_fixture,
            account_id=account_id,
            practice_dates=(_YESTERDAY - timedelta(days=1), _YESTERDAY),
        )

        _publish_due(inngest_fixture, account_id=account_id)
        inngest_fixture.wait_for_database(
            lambda session: len(_requested_rows(session, account_id)) >= 1
        )

        with inngest_fixture.inspection_session() as session:
            rows = _requested_rows(session, account_id)
            assert len(rows) == 1
            assert rows[0].payload == {
                'account_id': account_id,
                'local_date': '2026-09-15',
                'streak_days': 2,
                'expires_at': '2026-09-16T03:00:00Z',
            }
            profile = session.scalar(
                select(GamificationProfileModel).where(
                    GamificationProfileModel.account_id == account_id
                )
            )
            assert profile is not None
            assert profile.total_xp == 120
            assert profile.level == 2
            assert profile.streak_current == 2
            assert profile.streak_longest == 2
            assert profile.streak_latest_practice_date == _YESTERDAY
            assert profile.reminder_hour == 18
            assert profile.reminder_invite_answered_at is None
            assert _count(session, PracticeDayModel, account_id) == 2
            assert _count(session, XpGrantModel, account_id) == 0

    def test_should_record_nothing_for_ineligible_or_inactive_accounts(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        eligible = ids.generate()
        no_streak = ids.generate()
        practiced_today = ids.generate()
        broken_streak = ids.generate()
        wrong_hour = ids.generate()
        pending = ids.generate()
        deleted = ids.generate()
        _seed(inngest_fixture, account_id=eligible)
        _seed(inngest_fixture, account_id=no_streak, practice_dates=())
        _seed(
            inngest_fixture,
            account_id=practiced_today,
            practice_dates=(_YESTERDAY, _LOCAL_DATE),
        )
        _seed(
            inngest_fixture,
            account_id=broken_streak,
            practice_dates=(date(2026, 9, 11), date(2026, 9, 12)),
        )
        _seed(inngest_fixture, account_id=wrong_hour, hour=19)
        _seed(
            inngest_fixture,
            account_id=pending,
            status=AccountStatus.PENDING_CONFIRMATION,
        )
        _seed(inngest_fixture, account_id=deleted, status=AccountStatus.DELETED)

        ineligible = (
            no_streak,
            practiced_today,
            broken_streak,
            wrong_hour,
            pending,
            deleted,
        )
        event_ids = [
            _publish_due(inngest_fixture, account_id=item) for item in ineligible
        ]
        event_ids.append(_publish_due(inngest_fixture, account_id=eligible))
        for event_id in event_ids:
            inngest_fixture.wait_for_log(
                f'"event":"job.completed","event_id":"{event_id}"', timeout=90
            )

        with inngest_fixture.inspection_session() as session:
            assert len(_requested_rows(session, eligible)) == 1
            for account_id in ineligible:
                assert _requested_rows(session, account_id) == []

    def test_should_reject_an_invalid_payload_without_recording_anything(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed(inngest_fixture, account_id=account_id)
        valid: dict[str, object] = {
            'account_id': account_id,
            'local_date': '2026-09-15',
            'slot_start': _SLOT,
        }
        invalid_payloads: list[dict[str, object]] = [
            {**valid, 'account_id': '   '},
            {**valid, 'local_date': '15/09/2026'},
            {**valid, 'slot_start': 'not-a-date'},
            {**valid, 'slot_start': '2026-09-15T21:07:00Z'},
            {**valid, 'slot_start': '2026-09-15T18:00:00-03:00'},
            {**valid, 'unexpected': 'field'},
        ]

        for payload in invalid_payloads:
            event_id = ids.generate()
            inngest_fixture.publish(
                StreakReminderDueEvent.EVENT_NAME, payload, event_id=event_id
            )
            failure_log = inngest_fixture.wait_for_log(
                f'"event":"job.failed","event_id":"{event_id}"', timeout=60
            )
            assert '"error_code":"job_failed"' in failure_log
            assert '"exception_type":"NonRetriableError"' in failure_log

        with inngest_fixture.inspection_session() as session:
            assert _requested_rows(session, account_id) == []

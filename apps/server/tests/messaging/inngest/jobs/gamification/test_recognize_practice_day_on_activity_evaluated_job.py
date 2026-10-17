"""Real-runtime coverage for practice-day recognition from an evaluated Activity."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import PracticeDayModel
from shifu.learning.core.domain.enums import ActivityAttemptKind, ActivityDifficulty
from shifu.learning.core.domain.events import (
    ActivityEvaluatedEvent,
    ActivityEvaluatedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)
# 02:30Z is still the previous local day in Sao Paulo (UTC-3).
SUBMITTED_AT = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)
TIME_ZONE = 'America/Sao_Paulo'


def _practice_day_count(session: 'Session', account_id: str) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(PracticeDayModel)
            .where(PracticeDayModel.account_id == account_id)
        )
        or 0
    )


def _payload(
    account_id: str, ids: SystemIdentifierProvider
) -> ActivityEvaluatedPayload:
    return ActivityEvaluatedPayload(
        account_id=account_id,
        goal_id=ids.generate(),
        skill_experience_id=ids.generate(),
        skill_id=ids.generate(),
        competency_id=ids.generate(),
        activity_id=ids.generate(),
        attempt_id=ids.generate(),
        evaluation_id=ids.generate(),
        kind=ActivityAttemptKind.LEARNING,
        difficulty=ActivityDifficulty.MEDIUM,
        score='0',
        evaluated_at=NOW.isoformat().replace('+00:00', 'Z'),
        submitted_at=SUBMITTED_AT.isoformat().replace('+00:00', 'Z'),
        time_zone=TIME_ZONE,
    )


def _event_data(payload: ActivityEvaluatedPayload) -> dict[str, object]:
    return {
        'account_id': payload.account_id,
        'goal_id': payload.goal_id,
        'skill_experience_id': payload.skill_experience_id,
        'skill_id': payload.skill_id,
        'competency_id': payload.competency_id,
        'activity_id': payload.activity_id,
        'attempt_id': payload.attempt_id,
        'evaluation_id': payload.evaluation_id,
        'kind': payload.kind.value,
        'difficulty': payload.difficulty.value,
        'score': payload.score,
        'evaluated_at': payload.evaluated_at,
        'submitted_at': payload.submitted_at,
        'time_zone': payload.time_zone,
    }


def _seed_profile(inngest_fixture: 'InngestFixture', account_id: str) -> None:
    engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyGamificationDatabase(engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=account_id,
                    total_xp=0,
                    level=1,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
    finally:
        engine.dispose()


class TestRecognizePracticeDayOnActivityEvaluatedJob:
    def test_should_recognize_one_practice_day_under_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        event = ActivityEvaluatedEvent(payload=payload)
        data = _event_data(payload)

        inngest_fixture.publish(event.name, data, event_id=ids.generate())
        inngest_fixture.wait_for_database(
            lambda session: _practice_day_count(session, account_id) == 1
        )

        inngest_fixture.publish(event.name, data, event_id=ids.generate())
        inngest_fixture.wait_for_database(
            lambda session: _practice_day_count(session, account_id) == 1
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                stored = connection.execute(
                    select(
                        PracticeDayModel.practice_date, PracticeDayModel.time_zone
                    ).where(PracticeDayModel.account_id == account_id)
                ).all()
        finally:
            engine.dispose()

        assert len(stored) == 1
        # The submission's local date, not its UTC date.
        assert stored[0][0].isoformat() == '2026-02-28'
        assert stored[0][1] == TIME_ZONE

    def test_should_write_nothing_when_the_account_has_no_profile(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()

        payload = _payload(account_id, ids)
        event = ActivityEvaluatedEvent(payload=payload)
        inngest_fixture.publish(
            event.name, _event_data(payload), event_id=ids.generate()
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                count = (
                    connection.execute(
                        select(func.count())
                        .select_from(PracticeDayModel)
                        .where(PracticeDayModel.account_id == account_id)
                    ).scalar()
                    or 0
                )
        finally:
            engine.dispose()

        assert count == 0

    def test_should_recognize_the_day_when_the_time_zone_is_absent(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        """An unusable zone falls back to UTC rather than losing the day."""
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        data['time_zone'] = None
        event = ActivityEvaluatedEvent(payload=payload)

        inngest_fixture.publish(event.name, data, event_id=ids.generate())
        inngest_fixture.wait_for_database(
            lambda session: _practice_day_count(session, account_id) == 1
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                stored = connection.execute(
                    select(PracticeDayModel.practice_date).where(
                        PracticeDayModel.account_id == account_id
                    )
                ).all()
        finally:
            engine.dispose()

        # Resolved in UTC, so the UTC date rather than the Sao Paulo one.
        assert stored[0][0].isoformat() == '2026-03-01'

    def test_should_reject_an_unknown_field_without_writing(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        data['unexpected_field'] = 'nope'
        event = ActivityEvaluatedEvent(payload=payload)

        inngest_fixture.publish(event.name, data, event_id=ids.generate())

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                count = (
                    connection.execute(
                        select(func.count())
                        .select_from(PracticeDayModel)
                        .where(PracticeDayModel.account_id == account_id)
                    ).scalar()
                    or 0
                )
        finally:
            engine.dispose()

        assert count == 0

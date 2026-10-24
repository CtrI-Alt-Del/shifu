"""Real-runtime coverage for Activity XP production from an evaluated Activity."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    ActivityXpBalanceModel,
    ActivityXpRecognitionModel,
    PracticeDayModel,
    XpGrantModel,
)
from shifu.learning.core.domain.enums import ActivityAttemptKind, ActivityDifficulty
from shifu.learning.core.domain.events import (
    ActivityEvaluatedEvent,
    ActivityEvaluatedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)
SUBMITTED_AT = datetime(2026, 3, 1, 2, 30, tzinfo=UTC)
TIME_ZONE = 'America/Sao_Paulo'


def _grant_count(connection: 'Connection', account_id: str) -> int:
    return (
        connection.execute(
            select(func.count())
            .select_from(XpGrantModel)
            .where(XpGrantModel.account_id == account_id)
        ).scalar()
        or 0
    )


def _recognition_count(connection: 'Connection', account_id: str) -> int:
    return (
        connection.execute(
            select(func.count())
            .select_from(ActivityXpRecognitionModel)
            .where(ActivityXpRecognitionModel.account_id == account_id)
        ).scalar()
        or 0
    )


def _balance_count(connection: 'Connection', account_id: str) -> int:
    return (
        connection.execute(
            select(func.count())
            .select_from(ActivityXpBalanceModel)
            .where(ActivityXpBalanceModel.account_id == account_id)
        ).scalar()
        or 0
    )


def _payload(
    account_id: str,
    ids: SystemIdentifierProvider,
    *,
    activity_id: str | None = None,
    attempt_id: str | None = None,
    difficulty: ActivityDifficulty = ActivityDifficulty.EASY,
    score: str = '67',
    evaluated_at: datetime = NOW,
) -> ActivityEvaluatedPayload:
    return ActivityEvaluatedPayload(
        account_id=account_id,
        goal_id=ids.generate(),
        skill_experience_id=ids.generate(),
        skill_id=ids.generate(),
        competency_id=ids.generate(),
        activity_id=activity_id if activity_id is not None else ids.generate(),
        attempt_id=attempt_id if attempt_id is not None else ids.generate(),
        evaluation_id=ids.generate(),
        kind=ActivityAttemptKind.LEARNING,
        difficulty=difficulty,
        score=score,
        evaluated_at=evaluated_at.isoformat().replace('+00:00', 'Z'),
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


class TestRecognizeActivityXpOnActivityEvaluatedJob:
    def test_should_grant_activity_xp_exactly_once_under_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(
            account_id, ids, difficulty=ActivityDifficulty.EASY, score='67'
        )
        event = ActivityEvaluatedEvent(payload=payload)
        data = _event_data(payload)

        inngest_fixture.publish(event.name, data, event_id=ids.generate())
        inngest_fixture.wait_for_database(
            lambda session: (
                session.scalar(
                    select(func.count())
                    .select_from(XpGrantModel)
                    .where(XpGrantModel.account_id == account_id)
                )
                == 1
            )
        )

        inngest_fixture.publish(event.name, data, event_id=ids.generate())
        inngest_fixture.wait_for_database(
            lambda session: (
                session.scalar(
                    select(func.count())
                    .select_from(ActivityXpRecognitionModel)
                    .where(ActivityXpRecognitionModel.account_id == account_id)
                )
                == 1
            )
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                grants = connection.execute(
                    select(XpGrantModel.amount, XpGrantModel.fact_id).where(
                        XpGrantModel.account_id == account_id
                    )
                ).all()
                balances = connection.execute(
                    select(
                        ActivityXpBalanceModel.granted_xp,
                        ActivityXpBalanceModel.maximum_xp,
                    ).where(ActivityXpBalanceModel.account_id == account_id)
                ).all()
        finally:
            engine.dispose()

        assert len(grants) == 1
        assert grants[0][0] == 6
        assert grants[0][1] == payload.attempt_id
        assert len(balances) == 1
        assert balances[0] == (6, 10)

    def test_should_write_nothing_when_the_account_has_no_profile(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()

        payload = _payload(account_id, ids)
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            _event_data(payload),
            event_id=ids.generate(),
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                assert _grant_count(connection, account_id) == 0
                assert _recognition_count(connection, account_id) == 0
                assert _balance_count(connection, account_id) == 0
        finally:
            engine.dispose()

    def test_should_fail_non_retriably_for_an_unknown_difficulty(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        data['difficulty'] = 'impossible'
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            data,
            event_id=ids.generate(),
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                assert _grant_count(connection, account_id) == 0
                assert _recognition_count(connection, account_id) == 0
        finally:
            engine.dispose()

    def test_should_fail_non_retriably_for_an_out_of_range_score(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        data['score'] = '150'
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            data,
            event_id=ids.generate(),
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                assert _grant_count(connection, account_id) == 0
                assert _recognition_count(connection, account_id) == 0
        finally:
            engine.dispose()

    def test_should_fail_non_retriably_for_a_non_utc_evaluated_at(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        data['evaluated_at'] = '2026-01-01T00:00:00-03:00'
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            data,
            event_id=ids.generate(),
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                assert _grant_count(connection, account_id) == 0
                assert _recognition_count(connection, account_id) == 0
        finally:
            engine.dispose()

    def test_should_fail_non_retriably_for_a_missing_field(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        del data['skill_id']
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            data,
            event_id=ids.generate(),
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                assert _grant_count(connection, account_id) == 0
                assert _recognition_count(connection, account_id) == 0
        finally:
            engine.dispose()

    def test_should_fail_non_retriably_for_a_blank_account_id(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(account_id, ids)
        data = _event_data(payload)
        data['account_id'] = '   '
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            data,
            event_id=ids.generate(),
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                total_grants = connection.execute(
                    select(func.count()).select_from(XpGrantModel)
                ).scalar()
                total_recognitions = connection.execute(
                    select(func.count()).select_from(ActivityXpRecognitionModel)
                ).scalar()
        finally:
            engine.dispose()

        assert total_grants == 0
        assert total_recognitions == 0

    def test_should_fan_out_to_both_practice_day_and_activity_xp(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)

        payload = _payload(
            account_id, ids, difficulty=ActivityDifficulty.EASY, score='67'
        )
        inngest_fixture.publish(
            ActivityEvaluatedEvent(payload=payload).name,
            _event_data(payload),
            event_id=ids.generate(),
        )

        inngest_fixture.wait_for_database(
            lambda session: (
                (
                    session.scalar(
                        select(func.count())
                        .select_from(PracticeDayModel)
                        .where(PracticeDayModel.account_id == account_id)
                    )
                    == 1
                )
                and (
                    session.scalar(
                        select(func.count())
                        .select_from(XpGrantModel)
                        .where(XpGrantModel.account_id == account_id)
                    )
                    == 1
                )
            )
        )

    def test_should_split_the_activity_maximum_across_two_racing_attempts_on_a_new_activity(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        """Both deliveries race on an Activity with no balance row yet: the
        unique (account_id, activity_id) constraint aborts one transaction
        whole, and its Inngest retry settles on the committed balance."""
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        _seed_profile(inngest_fixture, account_id)
        activity_id = ids.generate()

        first = _payload(
            account_id,
            ids,
            activity_id=activity_id,
            difficulty=ActivityDifficulty.HARD,
            score='50',
        )
        second = _payload(
            account_id,
            ids,
            activity_id=activity_id,
            difficulty=ActivityDifficulty.HARD,
            score='80',
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(
                inngest_fixture.publish,
                ActivityEvaluatedEvent(payload=first).name,
                _event_data(first),
                ids.generate(),
            )
            executor.submit(
                inngest_fixture.publish,
                ActivityEvaluatedEvent(payload=second).name,
                _event_data(second),
                ids.generate(),
            )

        inngest_fixture.wait_for_database(
            lambda session: (
                session.scalar(
                    select(func.count())
                    .select_from(ActivityXpRecognitionModel)
                    .where(ActivityXpRecognitionModel.account_id == account_id)
                )
                == 2
            )
        )

        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                balances = connection.execute(
                    select(
                        ActivityXpBalanceModel.granted_xp,
                        ActivityXpBalanceModel.maximum_xp,
                    ).where(
                        ActivityXpBalanceModel.account_id == account_id,
                        ActivityXpBalanceModel.activity_id == activity_id,
                    )
                ).all()
                granted_sum = connection.execute(
                    select(func.sum(XpGrantModel.amount)).where(
                        XpGrantModel.account_id == account_id
                    )
                ).scalar_one()
        finally:
            engine.dispose()

        assert len(balances) == 1
        granted_xp, maximum_xp = balances[0]
        assert maximum_xp == 30
        assert granted_xp == 24
        assert granted_xp <= maximum_xp
        assert granted_sum == granted_xp

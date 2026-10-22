"""Real-runtime coverage for CA-05: first mastery grants 50 XP once.

Also covers SHIFU-81 CA-01/CA-02: the stored XP record carries the mastered
Competência's own name as its readable origin, and a redelivery of the same
event adds no second record.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SessionFactory

from shifu.curriculum.database.sqlalchemy.models import (
    CompetencyModel,
    CurriculumSequenceModel,
    SkillModel,
)
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    GamificationProfileModel,
    XpGrantModel,
)
from shifu.learning.core.domain.events import (
    CompetencyMasteredEvent,
    CompetencyMasteredPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)
COMPETENCY_NAME = 'Condicionais'
_EVENT_NAME = 'learning/competency-mastered'


class TestRecognizeCompetencyMasteredJob:
    def test_should_reject_a_malformed_event_without_crashing_the_worker(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        base_data: dict[str, object] = {
            'account_id': ids.generate(),
            'goal_id': ids.generate(),
            'skill_experience_id': ids.generate(),
            'skill_id': ids.generate(),
            'competency_id': ids.generate(),
            'progress': '100',
            'mastered_at': NOW.isoformat().replace('+00:00', 'Z'),
        }

        def publish_and_assert_failure(payload: dict[str, object]) -> None:
            event_id = ids.generate()
            inngest_fixture.publish(_EVENT_NAME, payload, event_id=event_id)
            failure_log = inngest_fixture.wait_for_log(
                f'"event":"job.failed","event_id":"{event_id}"',
                timeout=30,
            )
            assert '"job":"gamification.recognize_competency_mastered"' in failure_log
            assert '"exception_type":"NonRetriableError"' in failure_log

        # An empty identifier fails `_Payload.validate_identifier`.
        publish_and_assert_failure(
            {**base_data, 'account_id': '   '},
        )

        # An unparseable instant fails `_parse_utc_iso`'s format check.
        publish_and_assert_failure(
            {**base_data, 'mastered_at': 'not-a-date'},
        )

        # A syntactically valid but non-UTC instant fails the UTC check.
        publish_and_assert_failure(
            {**base_data, 'mastered_at': '2026-01-01T00:00:00+02:00'},
        )

    def test_should_grant_fifty_xp_once_on_first_mastery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        competency_id = ids.generate()
        skill_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            gamification_database = SqlalchemyGamificationDatabase(
                engine, id_provider=ids
            )
            with gamification_database.transaction() as repositories:
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        account_id=account_id,
                        total_xp=0,
                        level=1,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )
            # Real Curriculum content, so the real content provider resolves
            # the Competência's own name for the readable origin (SHIFU-81
            # RF-02) instead of falling back to the generic sentence.
            with SessionFactory(engine) as session:
                session.add(
                    SkillModel(
                        id=skill_id,
                        name=f'Habilidade {skill_id[:8]}',
                        description='Habilidade usada no teste de job.',
                        initial_diagnostic_activity_ids=[],
                    )
                )
                # The two models carry no ORM relationship, so the unit of
                # work would not order these inserts against the Competência's
                # foreign key on its own.
                session.flush()
                session.add(
                    CompetencyModel(
                        id=competency_id,
                        skill_id=skill_id,
                        name=COMPETENCY_NAME,
                        description='Competência usada no teste de job.',
                        position=1,
                    )
                )
                session.flush()
                # `get_skill_content` returns None for any Competência without
                # a sequence row, which would silently exercise the fallback
                # label instead of the resolved name.
                session.add(
                    CurriculumSequenceModel(competency_id=competency_id, items=[])
                )
                session.commit()
        finally:
            engine.dispose()

        payload = CompetencyMasteredPayload(
            account_id=account_id,
            goal_id=ids.generate(),
            skill_experience_id=ids.generate(),
            skill_id=skill_id,
            competency_id=competency_id,
            progress='100',
            mastered_at=NOW.isoformat().replace('+00:00', 'Z'),
        )
        event = CompetencyMasteredEvent(payload=payload)
        data: dict[str, object] = {
            'account_id': payload.account_id,
            'goal_id': payload.goal_id,
            'skill_experience_id': payload.skill_experience_id,
            'skill_id': payload.skill_id,
            'competency_id': payload.competency_id,
            'progress': payload.progress,
            'mastered_at': payload.mastered_at,
        }

        inngest_fixture.publish(event.name, data, event_id=ids.generate())

        # 50 XP base (CA-05) plus the 25 XP "primeiro-dominio" achievement
        # bonus that the GrantXpUseCase cascade also unlocks the first time
        # this account earns a COMPETENCY_MASTERY milestone.
        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 75
        )
        inngest_fixture.wait_for_database(
            lambda session: _mastery_labels(session, account_id) == [COMPETENCY_NAME]
        )

        # A redelivery of the same fact must add no second record.
        inngest_fixture.publish(event.name, data, event_id=ids.generate())

        inngest_fixture.wait_for_database(
            lambda session: (
                _total_xp(session, account_id) == 75
                and _mastery_labels(session, account_id) == [COMPETENCY_NAME]
            )
        )


def _total_xp(session: 'Session', account_id: str) -> int:
    profile = session.scalar(
        select(GamificationProfileModel).where(
            GamificationProfileModel.account_id == account_id
        )
    )
    return profile.total_xp if profile is not None else -1


def _mastery_labels(session: 'Session', account_id: str) -> list[str]:
    grants = (
        session.execute(
            select(XpGrantModel).where(XpGrantModel.account_id == account_id)
        )
        .scalars()
        .all()
    )
    origins = [cast('dict[str, str]', grant.origin) for grant in grants]
    return [
        origin['label']
        for origin in origins
        if origin['source'] == 'competency-mastery'
    ]

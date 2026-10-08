"""Real-runtime coverage for CA-03 and the CA-13 duplicate-delivery case."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.curriculum.core.domain.structures import CurriculumSequence
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.fakers.curriculum.entities import CompetencyFaker, SkillFaker
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    GamificationProfileModel,
    RewardedMilestoneModel,
    XpGrantModel,
)
from shifu.learning.core.domain.events import (
    DiagnosticCompletedEvent,
    DiagnosticCompletedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestRecognizeDiagnosticCompletedJob:
    def test_should_grant_xp_once_per_competency_under_duplicate_event_delivery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        skill_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            gamification_database = SqlalchemyGamificationDatabase(
                engine, id_provider=ids
            )
            with gamification_database.transaction() as repositories:
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        id=account_id,
                        total_xp=0,
                        level=1,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )
            curriculum_database = SqlalchemyCurriculumDatabase(engine)
            skill = SkillFaker.fake(id=skill_id)
            competencies = [
                CompetencyFaker.fake(skill_id=skill_id, position=position)
                for position in range(1, 4)
            ]
            with curriculum_database.transaction() as repositories:
                repositories.skills.add_many([skill])
                repositories.competencies.add_many(competencies)
                # DatabaseCurriculumContentProvider.get_skill_content treats a
                # competency with no CurriculumSequence row as incomplete
                # content and returns None for the whole skill (the use case
                # then no-ops, mirroring its "unknown skill" guard). An empty
                # sequence per competency is enough to make the content
                # lookup succeed without needing materials or activities.
                repositories.curriculum_sequences.add_many(
                    [
                        CurriculumSequence(competency_id=competency.id, items=())
                        for competency in competencies
                    ]
                )
        finally:
            engine.dispose()

        payload = DiagnosticCompletedPayload(
            account_id=account_id,
            goal_id=ids.generate(),
            skill_experience_id=ids.generate(),
            skill_id=skill_id,
            initial_progress='0',
            completed_at=NOW.isoformat().replace('+00:00', 'Z'),
        )
        event = DiagnosticCompletedEvent(payload=payload)
        event_data: dict[str, object] = {
            'account_id': payload.account_id,
            'goal_id': payload.goal_id,
            'skill_experience_id': payload.skill_experience_id,
            'skill_id': payload.skill_id,
            'initial_progress': payload.initial_progress,
            'completed_at': payload.completed_at,
        }

        inngest_fixture.publish(event.name, event_data, event_id=ids.generate())
        # 60 XP base (20 XP x 3 competencies, CA-03) plus the 25 XP
        # "diagnostico-primeiro-passo" achievement bonus that the
        # GrantXpUseCase cascade also unlocks the first time this account
        # earns a DIAGNOSTIC_COMPLETED milestone; the achievement grant is
        # its own XpGrant row alongside the base diagnostic grant.
        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 85
        )
        with inngest_fixture.inspection_session() as session:
            assert _milestone_count(session, account_id) == 1
            assert _xp_grant_count(session, account_id) == 2

        inngest_fixture.publish(event.name, event_data, event_id=ids.generate())
        # 60 XP base (20 XP x 3 competencies, CA-03) plus the 25 XP
        # "diagnostico-primeiro-passo" achievement bonus that the
        # GrantXpUseCase cascade also unlocks the first time this account
        # earns a DIAGNOSTIC_COMPLETED milestone; the achievement grant is
        # its own XpGrant row alongside the base diagnostic grant.
        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 85
        )
        with inngest_fixture.inspection_session() as session:
            assert _milestone_count(session, account_id) == 1
            assert _xp_grant_count(session, account_id) == 2

    def test_should_date_the_xp_grant_by_the_fact_date_not_the_processing_time(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        """CA-11: a late-arriving fact dates its grant by when it happened."""
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        skill_id = ids.generate()
        historical_completed_at = datetime(2025, 3, 10, tzinfo=UTC)
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            gamification_database = SqlalchemyGamificationDatabase(
                engine, id_provider=ids
            )
            with gamification_database.transaction() as repositories:
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        id=account_id,
                        total_xp=0,
                        level=1,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )
            curriculum_database = SqlalchemyCurriculumDatabase(engine)
            skill = SkillFaker.fake(id=skill_id)
            competency = CompetencyFaker.fake(skill_id=skill_id, position=1)
            with curriculum_database.transaction() as repositories:
                repositories.skills.add_many([skill])
                repositories.competencies.add_many([competency])
                repositories.curriculum_sequences.add_many(
                    [CurriculumSequence(competency_id=competency.id, items=())]
                )
        finally:
            engine.dispose()

        payload = DiagnosticCompletedPayload(
            account_id=account_id,
            goal_id=ids.generate(),
            skill_experience_id=ids.generate(),
            skill_id=skill_id,
            initial_progress='0',
            completed_at=historical_completed_at.isoformat().replace('+00:00', 'Z'),
        )
        event = DiagnosticCompletedEvent(payload=payload)
        inngest_fixture.publish(
            event.name,
            {
                'account_id': payload.account_id,
                'goal_id': payload.goal_id,
                'skill_experience_id': payload.skill_experience_id,
                'skill_id': payload.skill_id,
                'initial_progress': payload.initial_progress,
                'completed_at': payload.completed_at,
            },
            event_id=ids.generate(),
        )

        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 45
        )
        with inngest_fixture.inspection_session() as session:
            base_grant = session.scalar(
                select(XpGrantModel).where(
                    XpGrantModel.account_id == account_id,
                    XpGrantModel.origin == 'diagnostic',
                )
            )
            assert base_grant is not None
            assert base_grant.occurred_at == historical_completed_at
            assert base_grant.occurred_at != base_grant.granted_at


def _total_xp(session: 'Session', account_id: str) -> int:
    profile = session.get(GamificationProfileModel, account_id)
    return profile.total_xp if profile is not None else -1


def _milestone_count(session: 'Session', account_id: str) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(RewardedMilestoneModel)
            .where(RewardedMilestoneModel.account_id == account_id)
        )
        or 0
    )


def _xp_grant_count(session: 'Session', account_id: str) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(XpGrantModel)
            .where(XpGrantModel.account_id == account_id)
        )
        or 0
    )

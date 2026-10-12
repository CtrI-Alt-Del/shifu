"""Real-runtime coverage for CA-07 and the CA-13 duplicate-delivery case."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    GamificationProfileModel,
    XpGrantModel,
)
from shifu.learning.core.domain.events import (
    SkillCompletedEvent,
    SkillCompletedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestRecognizeSkillCompletedJob:
    def test_should_grant_xp_once_under_duplicate_event_delivery(
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
                        account_id=account_id,
                        total_xp=0,
                        level=1,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )
        finally:
            engine.dispose()

        payload = SkillCompletedPayload(
            account_id=account_id,
            goal_id=ids.generate(),
            skill_experience_id=ids.generate(),
            skill_id=skill_id,
            initial_progress='50',
            final_progress='100',
            completed_at=NOW.isoformat().replace('+00:00', 'Z'),
        )
        event = SkillCompletedEvent(payload=payload)
        event_data: dict[str, object] = {
            'account_id': payload.account_id,
            'goal_id': payload.goal_id,
            'skill_experience_id': payload.skill_experience_id,
            'skill_id': payload.skill_id,
            'initial_progress': payload.initial_progress,
            'final_progress': payload.final_progress,
            'completed_at': payload.completed_at,
        }

        inngest_fixture.publish(event.name, event_data, event_id=ids.generate())
        # 100 XP base (CA-07) plus the 50 XP "primeira-jornada" achievement
        # bonus that the GrantXpUseCase cascade also unlocks the first time
        # this account earns a SKILL_COMPLETION milestone; the achievement
        # grant is its own XpGrant row alongside the base one.
        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 150
        )
        with inngest_fixture.inspection_session() as session:
            assert _xp_grant_count(session, account_id) == 2

        inngest_fixture.publish(event.name, event_data, event_id=ids.generate())
        # 100 XP base (CA-07) plus the 50 XP "primeira-jornada" achievement
        # bonus that the GrantXpUseCase cascade also unlocks the first time
        # this account earns a SKILL_COMPLETION milestone; the achievement
        # grant is its own XpGrant row alongside the base one.
        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 150
        )
        with inngest_fixture.inspection_session() as session:
            assert _xp_grant_count(session, account_id) == 2


def _total_xp(session: 'Session', account_id: str) -> int:
    profile = session.scalar(
        select(GamificationProfileModel).where(
            GamificationProfileModel.account_id == account_id
        )
    )
    return profile.total_xp if profile is not None else -1


def _xp_grant_count(session: 'Session', account_id: str) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(XpGrantModel)
            .where(XpGrantModel.account_id == account_id)
        )
        or 0
    )

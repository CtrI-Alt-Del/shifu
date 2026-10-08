"""Real-runtime coverage for CA-05: first mastery grants 50 XP once."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, select

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import GamificationProfileModel
from shifu.learning.core.domain.events import (
    CompetencyMasteredEvent,
    CompetencyMasteredPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestRecognizeCompetencyMasteredJob:
    def test_should_grant_fifty_xp_once_on_first_mastery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        competency_id = ids.generate()
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

        payload = CompetencyMasteredPayload(
            account_id=account_id,
            goal_id=ids.generate(),
            skill_experience_id=ids.generate(),
            skill_id=ids.generate(),
            competency_id=competency_id,
            progress='100',
            mastered_at=NOW.isoformat().replace('+00:00', 'Z'),
        )
        event = CompetencyMasteredEvent(payload=payload)

        inngest_fixture.publish(
            event.name,
            {
                'account_id': payload.account_id,
                'goal_id': payload.goal_id,
                'skill_experience_id': payload.skill_experience_id,
                'skill_id': payload.skill_id,
                'competency_id': payload.competency_id,
                'progress': payload.progress,
                'mastered_at': payload.mastered_at,
            },
            event_id=ids.generate(),
        )

        # 50 XP base (CA-05) plus the 25 XP "primeiro-dominio" achievement
        # bonus that the GrantXpUseCase cascade also unlocks the first time
        # this account earns a COMPETENCY_MASTERY milestone.
        inngest_fixture.wait_for_database(
            lambda session: _total_xp(session, account_id) == 75
        )


def _total_xp(session: 'Session', account_id: str) -> int:
    profile = session.scalar(
        select(GamificationProfileModel).where(
            GamificationProfileModel.account_id == account_id
        )
    )
    return profile.total_xp if profile is not None else -1

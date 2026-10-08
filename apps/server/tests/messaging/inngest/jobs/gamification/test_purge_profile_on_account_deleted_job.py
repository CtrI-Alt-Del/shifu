"""Real-runtime coverage for CA-14: full purge on account deletion."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import (
    EarnedAchievementFaker,
    GamificationProfileFaker,
    RewardedMilestoneFaker,
    XpGrantFaker,
)
from shifu.gamification.core.domain.enums import AchievementCriterionKind, MilestoneKind
from shifu.gamification.core.domain.structures import AchievementCriterion
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    EarnedAchievementModel,
    GamificationProfileModel,
    RewardedMilestoneModel,
    XpGrantModel,
)
from shifu.identity.core.domain.events import (
    AccountDeletedEvent,
    AccountDeletedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestPurgeProfileOnAccountDeletedJob:
    def test_should_purge_every_gamification_table_for_the_account(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyGamificationDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        account_id=account_id,
                        total_xp=100,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )
                repositories.xp_grants.add(
                    XpGrantFaker.fake(
                        account_id=account_id,
                        amount=100,
                        occurred_at=NOW,
                        granted_at=NOW,
                    )
                )
                repositories.earned_achievements.try_add(
                    EarnedAchievementFaker.fake(
                        account_id=account_id,
                        achievement_id='primeiro-passo',
                        achievement_name='Primeiro Passo',
                        criterion=AchievementCriterion.create(
                            kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED,
                            target=1,
                        ),
                        xp_reward=25,
                        achieved_at=NOW,
                        granted_at=NOW,
                    )
                )
                repositories.rewarded_milestones.try_add(
                    RewardedMilestoneFaker.fake(
                        account_id=account_id,
                        kind=MilestoneKind.DIAGNOSIS,
                        subject_id=ids.generate(),
                        occurred_at=NOW,
                        rewarded_at=NOW,
                    )
                )
        finally:
            engine.dispose()

        deleted_at = NOW.isoformat().replace('+00:00', 'Z')
        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=deleted_at,
            )
        )
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
            },
            event_id=ids.generate(),
        )

        inngest_fixture.wait_for_database(
            lambda session: _all_purged(session, account_id)
        )


def _all_purged(session: 'Session', account_id: str) -> bool:
    return (
        _count(session, GamificationProfileModel, account_id) == 0
        and _count(session, XpGrantModel, account_id) == 0
        and _count(session, EarnedAchievementModel, account_id) == 0
        and _count(session, RewardedMilestoneModel, account_id) == 0
    )


def _count(
    session: 'Session',
    model: (
        type[GamificationProfileModel]
        | type[XpGrantModel]
        | type[EarnedAchievementModel]
        | type[RewardedMilestoneModel]
    ),
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

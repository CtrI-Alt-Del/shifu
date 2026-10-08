"""Real-runtime coverage for CA-14: full purge on account deletion."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import (
    AchievementUnlockFaker,
    GamificationProfileFaker,
    RewardedMilestoneFaker,
    XpGrantFaker,
)
from shifu.gamification.core.domain.enums import MilestoneType, XpOrigin
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    AchievementUnlockModel,
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
                        id=account_id,
                        total_xp=100,
                        level=1,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )
                repositories.xp_grants.add(
                    XpGrantFaker.fake(
                        account_id=account_id,
                        amount=100,
                        origin=XpOrigin.DIAGNOSTIC,
                        occurred_at=NOW,
                        granted_at=NOW,
                    )
                )
                repositories.achievement_unlocks.add(
                    AchievementUnlockFaker.fake(
                        account_id=account_id,
                        achievement_code='diagnostico-primeiro-passo',
                        unlocked_at=NOW,
                        granted_at=NOW,
                    )
                )
                repositories.rewarded_milestones.try_add(
                    RewardedMilestoneFaker.fake(
                        account_id=account_id,
                        milestone_type=MilestoneType.DIAGNOSTIC_COMPLETED,
                        reference_id=ids.generate(),
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
        session.get(GamificationProfileModel, account_id) is None
        and _count(session, XpGrantModel, account_id) == 0
        and _count(session, AchievementUnlockModel, account_id) == 0
        and _count(session, RewardedMilestoneModel, account_id) == 0
    )


def _count(
    session: 'Session',
    model: (
        type[XpGrantModel] | type[AchievementUnlockModel] | type[RewardedMilestoneModel]
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

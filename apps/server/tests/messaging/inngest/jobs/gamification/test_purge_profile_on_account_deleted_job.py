"""Real-runtime coverage for CA-14: full purge on account deletion."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, func, select

from shifu.fakers.gamification.entities import (
    ActivityXpBalanceFaker,
    ActivityXpRecognitionFaker,
    EarnedAchievementFaker,
    GamificationProfileFaker,
    RewardedMilestoneFaker,
    XpGrantFaker,
)
from shifu.gamification.core.domain.enums import AchievementCriterionKind, MilestoneKind
from shifu.gamification.core.domain.structures import AchievementCriterion
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    ActivityXpBalanceModel,
    ActivityXpRecognitionModel,
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
                        reminder_hour=7,
                        reminder_invite_answered_at=NOW,
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
                repositories.activity_xp_balances.add(
                    ActivityXpBalanceFaker.fake(
                        account_id=account_id,
                        maximum_xp=10,
                        granted_xp=6,
                        updated_at=NOW,
                    )
                )
                repositories.activity_xp_recognitions.try_add(
                    ActivityXpRecognitionFaker.fake(
                        account_id=account_id,
                        granted_xp=6,
                        occurred_at=NOW,
                        recognized_at=NOW,
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

    def test_should_remove_the_reminder_hour_and_invite_flag_and_replay_as_a_noop(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        other_account_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyGamificationDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
                for owner, hour in ((account_id, 7), (other_account_id, 21)):
                    repositories.profiles.add(
                        GamificationProfileFaker.fake(
                            account_id=owner,
                            reminder_hour=hour,
                            reminder_invite_answered_at=NOW,
                            created_at=NOW,
                            updated_at=NOW,
                        )
                    )
        finally:
            engine.dispose()
        with inngest_fixture.inspection_session() as session:
            stored = _reminder_state(session, account_id)
        assert stored == (7, NOW)

        deleted_at = NOW.isoformat().replace('+00:00', 'Z')
        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=deleted_at,
            )
        )
        payload: dict[str, object] = {
            'account_id': event.payload.account_id,
            'deleted_at': event.payload.deleted_at,
        }
        inngest_fixture.publish(event.name, payload, event_id=ids.generate())
        inngest_fixture.wait_for_database(
            lambda session: _count(session, GamificationProfileModel, account_id) == 0
        )

        with inngest_fixture.inspection_session() as session:
            assert _reminder_state(session, account_id) is None
            assert _reminder_state(session, other_account_id) == (21, NOW)

        replay_event_id = ids.generate()
        inngest_fixture.publish(event.name, payload, event_id=replay_event_id)
        inngest_fixture.wait_for_log(
            f'"event":"job.completed","event_id":"{replay_event_id}"',
            timeout=90,
        )

        with inngest_fixture.inspection_session() as session:
            assert _reminder_state(session, account_id) is None
            assert _reminder_state(session, other_account_id) == (21, NOW)


def _all_purged(session: 'Session', account_id: str) -> bool:
    return (
        _count(session, GamificationProfileModel, account_id) == 0
        and _count(session, XpGrantModel, account_id) == 0
        and _count(session, EarnedAchievementModel, account_id) == 0
        and _count(session, RewardedMilestoneModel, account_id) == 0
        and _count(session, ActivityXpBalanceModel, account_id) == 0
        and _count(session, ActivityXpRecognitionModel, account_id) == 0
    )


def _count(
    session: 'Session',
    model: (
        type[GamificationProfileModel]
        | type[XpGrantModel]
        | type[EarnedAchievementModel]
        | type[RewardedMilestoneModel]
        | type[ActivityXpBalanceModel]
        | type[ActivityXpRecognitionModel]
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


def _reminder_state(
    session: 'Session', account_id: str
) -> tuple[int, datetime | None] | None:
    profile = session.scalar(
        select(GamificationProfileModel).where(
            GamificationProfileModel.account_id == account_id
        )
    )
    if profile is None:
        return None
    return profile.reminder_hour, profile.reminder_invite_answered_at

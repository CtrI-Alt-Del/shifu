from datetime import datetime

from shifu.gamification.core.domain.entities import RewardedMilestone
from shifu.gamification.core.domain.enums import MilestoneKind, XpSource
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases.grant_xp_use_case import GrantXpUseCase
from shifu.shared.core.interfaces import IdentifierProvider


class RecognizeSkillCompletedUseCase:
    """Grant XP the first time a Habilidade is completed for this account.

    No-op without a Gamification profile for the account, or for a
    Habilidade (`skill_id`) already rewarded for this account under any
    Objetivo.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        identifier_provider: IdentifierProvider,
        grant_xp_use_case: GrantXpUseCase,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._grant_xp_use_case = grant_xp_use_case

    def execute(
        self,
        account_id: str,
        skill_id: str,
        skill_experience_id: str,
        *,
        occurred_at: datetime,
        now: datetime,
    ) -> None:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                return
            grant_id = self._identifier_provider.generate()
            milestone = RewardedMilestone.create(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                fact_id=skill_experience_id,
                kind=MilestoneKind.SKILL_COMPLETION,
                subject_id=skill_id,
                xp_grant_id=grant_id,
                occurred_at=occurred_at,
                rewarded_at=now,
            )
            if not repositories.rewarded_milestones.try_add(milestone):
                return
            amount = RewardedMilestone.xp_for(MilestoneKind.SKILL_COMPLETION)
            origin = XpOrigin(
                source=XpSource.SKILL_COMPLETION,
                reference_id=skill_id,
                label='Habilidade concluída pela primeira vez',
            )
            self._grant_xp_use_case.apply_within_transaction(
                repositories,
                account_id,
                grant_id,
                amount,
                origin,
                skill_experience_id,
                occurred_at=occurred_at,
                now=now,
            )

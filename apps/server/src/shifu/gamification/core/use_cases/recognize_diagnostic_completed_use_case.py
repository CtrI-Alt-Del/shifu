from datetime import datetime

from shifu.gamification.core.domain.entities import RewardedMilestone
from shifu.gamification.core.domain.enums import MilestoneKind, XpSource
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases.grant_xp_use_case import GrantXpUseCase
from shifu.shared.core.interfaces import CurriculumContentProvider, IdentifierProvider


class RecognizeDiagnosticCompletedUseCase:
    """Grant diagnostic XP the first time a Habilidade's diagnostic completes.

    No-op without a Gamification profile for the account, for an unknown
    skill, or for a Habilidade (`skill_id`) already rewarded for this
    account under any Objetivo. Idempotent via `RewardedMilestonesRepository
    .try_add`; the XP amount and the milestone insert commit atomically with
    the delegated `GrantXpUseCase` cascade.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        identifier_provider: IdentifierProvider,
        grant_xp_use_case: GrantXpUseCase,
    ) -> None:
        self._database = database
        self._curriculum_content_provider = curriculum_content_provider
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
            skill = self._curriculum_content_provider.get_skill_content(skill_id)
            if skill is None:
                return
            grant_id = self._identifier_provider.generate()
            milestone = RewardedMilestone.create(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                fact_id=skill_experience_id,
                kind=MilestoneKind.DIAGNOSIS,
                subject_id=skill_id,
                xp_grant_id=grant_id,
                occurred_at=occurred_at,
                rewarded_at=now,
            )
            if not repositories.rewarded_milestones.try_add(milestone):
                return
            amount = RewardedMilestone.xp_for(
                MilestoneKind.DIAGNOSIS, diagnosed_competencies=len(skill.competencies)
            )
            origin = XpOrigin(
                source=XpSource.DIAGNOSIS,
                reference_id=skill_id,
                label=f'Diagnóstico concluído: {skill.name}',
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

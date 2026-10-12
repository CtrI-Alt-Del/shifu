from datetime import datetime

from shifu.gamification.core.domain.achievement_catalog import ACHIEVEMENT_CATALOG
from shifu.gamification.core.domain.entities import (
    Achievement,
    EarnedAchievement,
    GamificationProfile,
    XpGrant,
)
from shifu.gamification.core.domain.enums import (
    AchievementCriterionKind,
    MilestoneKind,
)
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.core.domain.structures.xp_origin import XpSource
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.shared.core.interfaces import IdentifierProvider

_CRITERION_TO_MILESTONE: dict[AchievementCriterionKind, MilestoneKind] = {
    AchievementCriterionKind.DIAGNOSTICS_COMPLETED: MilestoneKind.DIAGNOSIS,
    AchievementCriterionKind.COMPETENCIES_MASTERED: MilestoneKind.COMPETENCY_MASTERY,
    AchievementCriterionKind.SKILLS_COMPLETED: MilestoneKind.SKILL_COMPLETION,
}


class GrantXpUseCase:
    """The single cascade orchestrator: apply XP, ratchet level, settle achievements.

    The whole cascade (XP -> level -> achievement -> XP, recursively) runs
    inside one `GamificationDatabase.transaction()` call; no partial cascade
    state is ever committed. `execute` is the standalone entry point for a
    direct caller and opens that transaction itself. The Learning-fact
    recognition use cases instead call `apply_within_transaction` with the
    repositories group they already opened for their own idempotency check,
    so the milestone insert and the whole XP/level/achievement cascade commit
    as a single unit.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        identifier_provider: IdentifierProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider

    def execute(
        self,
        account_id: str,
        grant_id: str,
        amount: int,
        origin: XpOrigin,
        fact_id: str,
        *,
        occurred_at: datetime,
        now: datetime,
    ) -> None:
        with self._database.transaction() as repositories:
            self.apply_within_transaction(
                repositories,
                account_id,
                grant_id,
                amount,
                origin,
                fact_id,
                occurred_at=occurred_at,
                now=now,
            )

    def apply_within_transaction(
        self,
        repositories: GamificationDatabaseRepositories,
        account_id: str,
        grant_id: str,
        amount: int,
        origin: XpOrigin,
        fact_id: str,
        *,
        occurred_at: datetime,
        now: datetime,
    ) -> None:
        profile = repositories.profiles.find_by_account_id(account_id)
        if profile is None:
            return
        earned_ids = {
            earned.achievement_id
            for earned in repositories.earned_achievements.find_many_by_account_id(
                account_id
            )
        }
        self._grant(
            repositories,
            profile,
            earned_ids,
            grant_id,
            amount,
            origin,
            fact_id,
            occurred_at=occurred_at,
            now=now,
        )
        repositories.profiles.update(profile)

    def _grant(
        self,
        repositories: GamificationDatabaseRepositories,
        profile: GamificationProfile,
        earned_ids: set[str],
        grant_id: str,
        amount: int,
        origin: XpOrigin,
        fact_id: str,
        *,
        occurred_at: datetime,
        now: datetime,
    ) -> None:
        repositories.xp_grants.add(
            XpGrant.create(
                id=grant_id,
                account_id=profile.account_id,
                fact_id=fact_id,
                amount=amount,
                origin=origin,
                occurred_at=occurred_at,
                granted_at=now,
            )
        )
        profile.add_xp(amount, granted_at=now)
        self._settle_achievements(
            repositories,
            profile,
            earned_ids,
            occurred_at=occurred_at,
            now=now,
        )

    def _settle_achievements(
        self,
        repositories: GamificationDatabaseRepositories,
        profile: GamificationProfile,
        earned_ids: set[str],
        *,
        occurred_at: datetime,
        now: datetime,
    ) -> None:
        while True:
            counts = self._counters(repositories, profile.account_id)
            newly_eligible = [
                achievement
                for achievement in ACHIEVEMENT_CATALOG
                if achievement.is_active
                and achievement.id not in earned_ids
                and self._is_satisfied(achievement, profile, counts)
            ]
            if not newly_eligible:
                return
            # Unlock every achievement found eligible in this one pass first,
            # all sharing this pass's `occurred_at` (they were all already
            # satisfied before any of their own XP rewards were applied, so
            # none of them was "caused by" another's cascade). Only apply
            # their XP rewards afterward: a reward that itself unlocks a
            # further achievement starts a deeper, `now`-dated pass.
            newly_earned: list[tuple[Achievement, str]] = []
            for achievement in newly_eligible:
                earned_ids.add(achievement.id)
                earned_id = self._identifier_provider.generate()
                repositories.earned_achievements.try_add(
                    EarnedAchievement.create(
                        id=earned_id,
                        account_id=profile.account_id,
                        achievement_id=achievement.id,
                        achievement_name=achievement.name,
                        criterion=achievement.criterion,
                        xp_reward=achievement.xp_reward,
                        achieved_at=occurred_at,
                        granted_at=now,
                    )
                )
                newly_earned.append((achievement, earned_id))
            for achievement, earned_id in newly_earned:
                self._grant(
                    repositories,
                    profile,
                    earned_ids,
                    self._identifier_provider.generate(),
                    achievement.xp_reward,
                    XpOrigin(
                        source=XpSource.ACHIEVEMENT,
                        reference_id=achievement.id,
                        label=f'Conquista: {achievement.name}',
                    ),
                    earned_id,
                    occurred_at=now,
                    now=now,
                )

    @staticmethod
    def _counters(
        repositories: GamificationDatabaseRepositories,
        account_id: str,
    ) -> dict[MilestoneKind, int]:
        return {
            kind: repositories.rewarded_milestones.count_by_account_id_and_kind(
                account_id, kind
            )
            for kind in MilestoneKind
        }

    @staticmethod
    def _is_satisfied(
        achievement: Achievement,
        profile: GamificationProfile,
        counts: dict[MilestoneKind, int],
    ) -> bool:
        kind = achievement.criterion.kind
        target = achievement.criterion.target
        if kind is AchievementCriterionKind.LEVEL:
            return profile.level >= target
        if kind is AchievementCriterionKind.LONGEST_STREAK:
            return profile.streak.longest >= target
        milestone_kind = _CRITERION_TO_MILESTONE.get(kind)
        if milestone_kind is None:
            return False
        return counts[milestone_kind] >= target

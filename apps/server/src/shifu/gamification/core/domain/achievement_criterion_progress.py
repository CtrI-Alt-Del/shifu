from collections.abc import Mapping

from shifu.gamification.core.domain.enums import (
    AchievementCriterionKind,
    MilestoneKind,
)
from shifu.gamification.core.domain.structures.achievement_criterion import (
    AchievementCriterion,
)

_CRITERION_TO_MILESTONE: dict[AchievementCriterionKind, MilestoneKind] = {
    AchievementCriterionKind.DIAGNOSTICS_COMPLETED: MilestoneKind.DIAGNOSIS,
    AchievementCriterionKind.COMPETENCIES_MASTERED: MilestoneKind.COMPETENCY_MASTERY,
    AchievementCriterionKind.SKILLS_COMPLETED: MilestoneKind.SKILL_COMPLETION,
}


def achievement_criterion_progress(
    criterion: AchievementCriterion,
    *,
    level: int,
    longest_streak: int,
    milestone_counts: Mapping[MilestoneKind, int],
) -> tuple[int, int]:
    """(current, target) for one criterion; current is not clamped.

    Shared by the Conquistas tab and the overview's next-achievement choice so
    both surfaces always read the same numbers for the same account.
    """
    kind = criterion.kind
    target = criterion.target
    if kind is AchievementCriterionKind.LEVEL:
        return level, target
    if kind is AchievementCriterionKind.LONGEST_STREAK:
        return longest_streak, target
    milestone_kind = _CRITERION_TO_MILESTONE[kind]
    return milestone_counts[milestone_kind], target

from shifu.gamification.core.domain.enums.achievement_criterion_kind import (
    AchievementCriterionKind,
)
from shifu.gamification.core.domain.enums.achievement_family import AchievementFamily
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.structures.achievement_criterion import (
    AchievementCriterion,
)
from shifu.shared.core.domain.entities import frozen_entity
from shifu.shared.core.domain.structures import BoundedInteger, EnumValue, NonEmptyText

_FAMILY_CRITERIA: dict[AchievementFamily, AchievementCriterionKind] = {
    AchievementFamily.DIAGNOSIS: AchievementCriterionKind.DIAGNOSTICS_COMPLETED,
    AchievementFamily.MASTERY: AchievementCriterionKind.COMPETENCIES_MASTERED,
    AchievementFamily.COMPLETION: AchievementCriterionKind.SKILLS_COMPLETED,
    AchievementFamily.STREAK: AchievementCriterionKind.LONGEST_STREAK,
    AchievementFamily.LEVEL: AchievementCriterionKind.LEVEL,
}


@frozen_entity
class Achievement:
    id: str
    name: str
    description: str
    family: AchievementFamily
    criterion: AchievementCriterion
    xp_reward: int
    is_active: bool = True

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidGamificationError)
        NonEmptyText.create(self.name, error_type=InvalidGamificationError)
        NonEmptyText.create(self.description, error_type=InvalidGamificationError)
        EnumValue.create(
            self.family, AchievementFamily, error_type=InvalidGamificationError
        )
        BoundedInteger.create(
            self.xp_reward, minimum=1, error_type=InvalidGamificationError
        )
        if (
            type(self.criterion) is not AchievementCriterion
            or self.criterion.kind is not _FAMILY_CRITERIA[self.family]
        ):
            raise InvalidGamificationError
        if type(self.is_active) is not bool:
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        name: str,
        description: str,
        family: AchievementFamily,
        criterion: AchievementCriterion,
        xp_reward: int,
        is_active: bool = True,
    ) -> 'Achievement':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            name=NonEmptyText.create(name, error_type=InvalidGamificationError).value,
            description=NonEmptyText.create(
                description, error_type=InvalidGamificationError
            ).value,
            family=family,
            criterion=criterion,
            xp_reward=xp_reward,
            is_active=is_active,
        )

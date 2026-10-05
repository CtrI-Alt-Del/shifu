from shifu.gamification.core.domain.enums.achievement_criterion_kind import (
    AchievementCriterionKind,
)
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.structures import BoundedInteger, EnumValue, structure


@structure
class AchievementCriterion:
    kind: AchievementCriterionKind
    target: int

    def __post_init__(self) -> None:
        EnumValue.create(
            self.kind, AchievementCriterionKind, error_type=InvalidGamificationError
        )
        BoundedInteger.create(
            self.target, minimum=1, error_type=InvalidGamificationError
        )

    @classmethod
    def create(
        cls, *, kind: AchievementCriterionKind, target: int
    ) -> 'AchievementCriterion':
        return cls(kind=kind, target=target)

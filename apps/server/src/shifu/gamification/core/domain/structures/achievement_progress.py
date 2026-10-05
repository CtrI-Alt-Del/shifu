from datetime import datetime

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.structures import (
    AwareTimestamp,
    BoundedInteger,
    NonEmptyText,
    structure,
)


@structure
class AchievementProgress:
    achievement_id: str
    current_value: int
    target_value: int
    achieved_at: datetime | None = None

    def __post_init__(self) -> None:
        NonEmptyText.create(self.achievement_id, error_type=InvalidGamificationError)
        BoundedInteger.create(self.current_value, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.target_value, minimum=1, error_type=InvalidGamificationError
        )
        if self.achieved_at is not None:
            AwareTimestamp.create(self.achieved_at, error_type=InvalidGamificationError)

    @classmethod
    def create(
        cls,
        *,
        achievement_id: str,
        current_value: int,
        target_value: int,
        achieved_at: datetime | None = None,
    ) -> 'AchievementProgress':
        return cls(
            achievement_id=NonEmptyText.create(
                achievement_id, error_type=InvalidGamificationError
            ).value,
            current_value=current_value,
            target_value=target_value,
            achieved_at=achieved_at,
        )

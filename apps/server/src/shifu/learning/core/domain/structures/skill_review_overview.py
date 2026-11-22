from decimal import Decimal

from shifu.shared.core.domain.structures import Percentage, structure


@structure
class SkillReviewOverview:
    attempt_count: int
    latest_score: Decimal | None

    def __post_init__(self) -> None:
        if self.attempt_count < 0:
            raise ValueError('The review attempt count cannot be negative.')

        if self.latest_score is not None:
            Percentage.create(self.latest_score)

from datetime import date
from decimal import Decimal

from shifu.learning.core.domain.enums import StartingPointCoverage
from shifu.learning.core.domain.structures.competency_completion_overview import (
    CompetencyCompletionOverview,
)
from shifu.learning.core.domain.structures.skill_review_overview import (
    SkillReviewOverview,
)
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class SkillCompletionOverview:
    started_on: date
    completed_on: date
    duration_days: int
    completed_by_diagnosis: bool
    learning_activity_count: int | None
    learning_attempt_count: int | None
    initial_result: Decimal | None
    initial_result_coverage: StartingPointCoverage
    final_result: Decimal
    competencies: tuple[CompetencyCompletionOverview, ...]
    review: SkillReviewOverview

    def __post_init__(self) -> None:
        if self.completed_on < self.started_on:
            raise ValueError('The Skill cannot complete before it starts.')

        if self.duration_days != (self.completed_on - self.started_on).days:
            raise ValueError('The duration is the difference between both days.')

        counts = (self.learning_activity_count, self.learning_attempt_count)
        if self.completed_by_diagnosis:
            if any(count is not None for count in counts):
                raise ValueError('A diagnosis completion has no learning counts.')
        elif any(count is None for count in counts):
            raise ValueError('A learning completion requires both learning counts.')

        if any(count is not None and count < 0 for count in counts):
            raise ValueError('Learning counts cannot be negative.')

        if (
            self.initial_result is None
            and self.initial_result_coverage is not StartingPointCoverage.UNKNOWN
        ):
            raise ValueError('A missing initial result requires unknown coverage.')

        if self.initial_result is not None:
            Percentage.create(self.initial_result)
        Percentage.create(self.final_result)

from datetime import date
from decimal import Decimal

from shifu.learning.core.domain.enums import StartingPointCoverage
from shifu.shared.core.domain.structures import Percentage, structure


@structure
class CompetencyCompletionOverview:
    competency_id: str
    competency_name: str
    position: int
    initial_progress: Decimal | None
    initial_coverage: StartingPointCoverage
    final_progress: Decimal
    mastered_on: date

    def __post_init__(self) -> None:
        if (self.initial_progress is None) is not (
            self.initial_coverage is StartingPointCoverage.UNKNOWN
        ):
            raise ValueError(
                'A starting value is absent exactly when its coverage is unknown.'
            )

        if self.initial_progress is not None:
            Percentage.create(self.initial_progress)
        Percentage.create(self.final_progress)

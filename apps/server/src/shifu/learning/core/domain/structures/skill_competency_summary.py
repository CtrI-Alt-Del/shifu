from decimal import Decimal

from shifu.learning.core.domain.enums import (
    CompetencyAvailability,
    CompetencyProgressStatus,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_percentage


@structure
class SkillCompetencySummary:
    competency_id: str
    competency_name: str
    position: int
    progress: Decimal | None
    status: CompetencyProgressStatus | None
    availability: CompetencyAvailability
    is_focus: bool
    coverage_complete: bool = False

    def __post_init__(self) -> None:
        if self.progress is not None:
            require_percentage(self.progress)
        if self.position < 1:
            raise ValueError('Curricular position starts at one.')

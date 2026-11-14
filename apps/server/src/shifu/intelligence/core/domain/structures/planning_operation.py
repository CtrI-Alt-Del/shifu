from datetime import datetime

from shifu.intelligence.core.domain.enums.planning_operation_kind import (
    PlanningOperationKind,
)
from shifu.intelligence.core.domain.enums.planning_operation_stage import (
    PlanningOperationStage,
)
from shifu.shared.core.domain.structures import structure


@structure
class PlanningOperation:
    id: str
    kind: PlanningOperationKind
    started_at: datetime
    stage: PlanningOperationStage | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError('An operation needs an identifier.')
        if self.started_at.tzinfo is None:
            raise ValueError('An operation start must be timezone-aware.')

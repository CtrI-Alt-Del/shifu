from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class PlanningOperationRequestedPayload:
    planning_id: str
    operation_id: str
    generation: int


@structure
class PlanningOperationRequestedEvent(Event[PlanningOperationRequestedPayload]):
    name: str = field(default='intelligence/planning.operation.requested', init=False)

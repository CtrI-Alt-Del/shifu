from shifu.intelligence.core.domain.structures import PlanningOperationResult
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.shared.core.interfaces import ClockProvider


class CompletePlanningOperationUseCase:
    def __init__(
        self, sessions: PlanningSessionsRepository, clock: ClockProvider
    ) -> None:
        self._sessions = sessions
        self._clock = clock

    def execute(
        self,
        planning_id: str,
        operation_id: str,
        generation: int,
        result: PlanningOperationResult,
    ) -> bool:
        session = self._sessions.find_by_id(planning_id)
        if session is None:
            return False
        if not session.complete(operation_id, generation, result, self._clock.now()):
            return False
        # A cancel or restart between the read and this write makes the result stale.
        return self._sessions.update(session)

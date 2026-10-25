from shifu.intelligence.core.domain.enums import PlanningOperationStage
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.shared.core.interfaces import ClockProvider


class ReportPlanningProgressUseCase:
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
        stage: PlanningOperationStage,
    ) -> bool:
        session = self._sessions.find_by_id(planning_id)
        if session is None:
            return False
        if not session.report_progress(
            operation_id, generation, stage, self._clock.now()
        ):
            return False
        # Losing the compare-and-set means a cancel or restart won; nothing to report.
        return self._sessions.update(session)

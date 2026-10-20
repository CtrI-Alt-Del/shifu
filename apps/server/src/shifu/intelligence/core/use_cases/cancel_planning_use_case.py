from shifu.intelligence.core.domain.errors import PlanningSessionNotFoundError
from shifu.intelligence.core.interfaces import PlanningSessionsRepository


class CancelPlanningUseCase:
    def __init__(self, sessions: PlanningSessionsRepository) -> None:
        self._sessions = sessions

    def execute(self, account_id: str, planning_id: str) -> None:
        session = self._sessions.find_by_id(planning_id)
        if session is None:
            # Cancelling an expired or already cancelled planning is idempotent.
            return
        if session.account_id != account_id:
            raise PlanningSessionNotFoundError
        self._sessions.remove(planning_id)

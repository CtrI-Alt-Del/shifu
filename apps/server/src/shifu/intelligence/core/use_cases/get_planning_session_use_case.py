from datetime import timedelta

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.errors import PlanningSessionNotFoundError
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.shared.core.interfaces import ClockProvider


class GetPlanningSessionUseCase:
    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        clock: ClockProvider,
        operation_timeout: timedelta,
    ) -> None:
        self._sessions = sessions
        self._clock = clock
        self._operation_timeout = operation_timeout

    def execute(self, account_id: str, planning_id: str) -> PlanningSession:
        session = self._owned(account_id, planning_id)
        now = self._clock.now()
        if not session.expire_operation(now, self._operation_timeout):
            return session
        if self._sessions.update(session):
            return session
        # Another request moved the planning first; expose that newer state instead.
        refreshed = self._owned(account_id, planning_id)
        refreshed.expire_operation(now, self._operation_timeout)
        return refreshed

    def _owned(self, account_id: str, planning_id: str) -> PlanningSession:
        session = self._sessions.find_by_id(planning_id)
        if session is None or session.account_id != account_id:
            raise PlanningSessionNotFoundError
        return session

from shifu.intelligence.core.interfaces import PlanningSessionsRepository


class PurgePlanningSessionsForAccountUseCase:
    """Remove all Intelligence planning sessions owned by one account."""

    def __init__(self, planning_sessions: PlanningSessionsRepository) -> None:
        self._planning_sessions = planning_sessions

    def execute(self, account_id: str) -> int:
        if not account_id.strip():
            raise ValueError('An account id is required to purge planning sessions.')
        return self._planning_sessions.remove_by_account_id(account_id)

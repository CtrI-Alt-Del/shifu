from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class StartPlanningUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._id_provider = id_provider
        self._clock_provider = clock_provider

    def execute(self, account_id: str, initial_intent: str) -> PlanningSession:
        planning_session = PlanningSession(
            id=self._id_provider.generate(),
            account_id=account_id,
            initial_intent=initial_intent,
            created_at=self._clock_provider.now(),
        )
        with self._database.transaction() as repositories:
            repositories.planning_sessions.add(planning_session)
        return planning_session

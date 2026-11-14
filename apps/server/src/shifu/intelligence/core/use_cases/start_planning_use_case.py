from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    PlanningSessionsRepository,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class StartPlanningUseCase:
    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        database: IntelligenceDatabase,
        access: MentorAccessProvider,
        identifiers: IdentifierProvider,
        clock: ClockProvider,
    ) -> None:
        self._sessions = sessions
        self._database = database
        self._access = access
        self._identifiers = identifiers
        self._clock = clock

    def execute(self, account_id: str, intent: str) -> PlanningSession:
        planning_id = self._identifiers.generate()
        grant = self._access.authorize(account_id, planning_id)
        operation_id = self._identifiers.generate()
        session = PlanningSession.start(
            planning_id,
            account_id,
            grant.access_revision,
            intent,
            operation_id,
            self._clock.now(),
        )
        # The temporary state exists before the worker can be asked to process it.
        self._sessions.add(session)
        with self._database.transaction() as repositories:
            repositories.events.add(
                PlanningOperationRequestedEvent(
                    payload=PlanningOperationRequestedPayload(
                        planning_id=planning_id,
                        operation_id=operation_id,
                        generation=session.generation,
                    )
                )
            )
        return session

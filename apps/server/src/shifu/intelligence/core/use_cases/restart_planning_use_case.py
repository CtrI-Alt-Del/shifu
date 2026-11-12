from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.errors import (
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import AiQuotaPolicy
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases.ai_quota_ledger import AiQuotaLedger
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class RestartPlanningUseCase:
    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        database: IntelligenceDatabase,
        access: MentorAccessProvider,
        identifiers: IdentifierProvider,
        clock: ClockProvider,
        quota_policy: AiQuotaPolicy,
        quota_calendar: AiQuotaCalendarProvider,
    ) -> None:
        self._sessions = sessions
        self._database = database
        self._access = access
        self._identifiers = identifiers
        self._clock = clock
        self._ledger = AiQuotaLedger(quota_policy, quota_calendar, clock)

    def execute(
        self, account_id: str, planning_id: str, intent: str
    ) -> PlanningSession:
        session = self._sessions.find_by_id(planning_id)
        if session is None or session.account_id != account_id:
            raise PlanningSessionNotFoundError
        grant = self._access.authorize(account_id, planning_id)
        operation_id = self._identifiers.generate()
        # A new generation discards answers and proposal; late results of the old one
        # no longer match and are dropped.
        session.restart(intent, grant.access_revision, operation_id, self._clock.now())
        # Admission commits before the planning is written to Redis.
        with self._database.transaction() as repositories:
            self._ledger.admit(
                repositories,
                AiQuotaRequestKind.PLANNING_OPERATION,
                operation_id,
                account_id,
            )
        if not self._sessions.update(session):
            raise PlanningOperationConflictError
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

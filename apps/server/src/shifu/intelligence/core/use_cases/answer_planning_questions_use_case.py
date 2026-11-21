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
from shifu.intelligence.core.domain.structures import AiQuotaPolicy, PlanningAnswer
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases.ai_quota_ledger import AiQuotaLedger
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class AnswerPlanningQuestionsUseCase:
    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        database: IntelligenceDatabase,
        identifiers: IdentifierProvider,
        clock: ClockProvider,
        quota_policy: AiQuotaPolicy,
        quota_calendar: AiQuotaCalendarProvider,
    ) -> None:
        self._sessions = sessions
        self._database = database
        self._identifiers = identifiers
        self._clock = clock
        self._ledger = AiQuotaLedger(quota_policy, quota_calendar, clock)

    def execute(
        self,
        account_id: str,
        planning_id: str,
        batch_id: str,
        answers: tuple[PlanningAnswer, ...],
    ) -> PlanningSession:
        session = self._sessions.find_by_id(planning_id)
        if session is None or session.account_id != account_id:
            raise PlanningSessionNotFoundError
        operation_id = self._identifiers.generate()
        session.submit_answers(batch_id, answers, operation_id, self._clock.now())
        # Answers to a running planning are never refused for quota. The operation is
        # registered so its usage is charged; the register commits before Redis.
        with self._database.transaction() as repositories:
            self._ledger.register(
                repositories,
                AiQuotaRequestKind.PLANNING_OPERATION,
                operation_id,
                account_id,
            )
        # The compare-and-set loses when a concurrent submission started first.
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

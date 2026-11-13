import logging

from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    PlanningOperationResultKind,
)
from shifu.intelligence.core.domain.structures import (
    AiQuotaPolicy,
    PlanningOperationResult,
)
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases.ai_quota_ledger import AiQuotaLedger
from shifu.shared.core.interfaces import ClockProvider

_logger = logging.getLogger(__name__)

_REFUNDED_RESULT_KINDS = frozenset(
    {PlanningOperationResultKind.FAILED, PlanningOperationResultKind.VALIDATION_FAILED}
)


class CompletePlanningOperationUseCase:
    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        clock: ClockProvider,
        database: IntelligenceDatabase,
        quota_policy: AiQuotaPolicy,
        quota_calendar: AiQuotaCalendarProvider,
    ) -> None:
        self._sessions = sessions
        self._clock = clock
        self._database = database
        self._ledger = AiQuotaLedger(quota_policy, quota_calendar, clock)

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
        if not self._sessions.update(session):
            return False
        # Only an accepted write refunds: a cancel or completion that won the race
        # keeps its charge.
        if result.kind in _REFUNDED_RESULT_KINDS:
            self._refund(operation_id)
        return True

    def _refund(self, operation_id: str) -> None:
        try:
            with self._database.transaction() as repositories:
                self._ledger.refund(
                    repositories, AiQuotaRequestKind.PLANNING_OPERATION, operation_id
                )
        except Exception:  # noqa: BLE001 - the Redis result is final; a lost refund must not fail it.
            _logger.warning(
                'ai_quota_refund_failed kind=%s request_id=%s',
                AiQuotaRequestKind.PLANNING_OPERATION.value,
                operation_id,
            )

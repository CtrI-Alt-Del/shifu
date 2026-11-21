import logging
from datetime import timedelta

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.errors import PlanningSessionNotFoundError
from shifu.intelligence.core.domain.structures import AiQuotaPolicy
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases.ai_quota_ledger import AiQuotaLedger
from shifu.shared.core.interfaces import ClockProvider

_logger = logging.getLogger(__name__)


class GetPlanningSessionUseCase:
    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        clock: ClockProvider,
        operation_timeout: timedelta,
        database: IntelligenceDatabase,
        quota_policy: AiQuotaPolicy,
        quota_calendar: AiQuotaCalendarProvider,
    ) -> None:
        self._sessions = sessions
        self._clock = clock
        self._operation_timeout = operation_timeout
        self._database = database
        self._ledger = AiQuotaLedger(quota_policy, quota_calendar, clock)

    def execute(self, account_id: str, planning_id: str) -> PlanningSession:
        session = self._owned(account_id, planning_id)
        now = self._clock.now()
        operation = session.operation
        if not session.expire_operation(now, self._operation_timeout):
            return session
        if self._sessions.update(session):
            # Only the write that records the expiry refunds its operation.
            if operation is not None:
                self._refund(operation.id)
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

    def _refund(self, operation_id: str) -> None:
        try:
            with self._database.transaction() as repositories:
                self._ledger.refund(
                    repositories, AiQuotaRequestKind.PLANNING_OPERATION, operation_id
                )
        except Exception:  # noqa: BLE001 - the expiry is already stored; a lost refund must not fail the read.
            _logger.warning(
                'ai_quota_refund_failed kind=%s request_id=%s',
                AiQuotaRequestKind.PLANNING_OPERATION.value,
                operation_id,
            )

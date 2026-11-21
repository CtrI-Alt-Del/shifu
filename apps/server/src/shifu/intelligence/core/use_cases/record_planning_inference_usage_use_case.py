from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.core.domain.structures import AiQuotaPolicy, AiTokenCount
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
)
from shifu.intelligence.core.use_cases.ai_quota_ledger import AiQuotaLedger
from shifu.shared.core.interfaces import ClockProvider


class RecordPlanningInferenceUsageUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        quota_policy: AiQuotaPolicy,
        quota_calendar: AiQuotaCalendarProvider,
        clock: ClockProvider,
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._ledger: AiQuotaLedger = AiQuotaLedger(quota_policy, quota_calendar, clock)

    def execute(self, operation_id: str, cumulative: AiTokenCount) -> None:
        """Charge the operation up to its accumulated token count; repeats are idempotent."""
        with self._database.transaction() as repositories:
            self._ledger.charge(
                repositories,
                AiQuotaRequestKind.PLANNING_OPERATION,
                operation_id,
                (cumulative,),
            )

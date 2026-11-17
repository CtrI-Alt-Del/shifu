from shifu.intelligence.core.domain.enums import AiQuotaStatus
from shifu.intelligence.core.domain.structures import AiQuotaPolicy, AiQuotaUsage
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
)
from shifu.shared.core.interfaces import ClockProvider

NEAR_LIMIT_PERCENTAGE = 80


class GetAiQuotaUsageUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        policy: AiQuotaPolicy,
        calendar: AiQuotaCalendarProvider,
        clock: ClockProvider,
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._policy: AiQuotaPolicy = policy
        self._calendar: AiQuotaCalendarProvider = calendar
        self._clock: ClockProvider = clock

    def execute(self, account_id: str) -> AiQuotaUsage:
        month = self._calendar.month_of(self._clock.now())
        # A short read without locks: the reading never blocks a charge.
        with self._database.transaction() as repositories:
            quota_month = repositories.ai_quota_months.find_by_account_and_month(
                account_id, month
            )
        used = 0 if quota_month is None else quota_month.used_units
        limit = (
            self._policy.monthly_limit_units
            if quota_month is None
            else quota_month.limit_units
        )
        percentage = used * 100 // limit
        return AiQuotaUsage(
            percentage=percentage,
            status=self._status(used, limit, percentage),
            renews_on=self._calendar.renewal_of(month),
        )

    @staticmethod
    def _status(used: int, limit: int, percentage: int) -> AiQuotaStatus:
        if used >= limit:
            return AiQuotaStatus.BLOCKED
        if percentage >= NEAR_LIMIT_PERCENTAGE:
            return AiQuotaStatus.NEAR_LIMIT
        return AiQuotaStatus.NORMAL

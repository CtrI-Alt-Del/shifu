from datetime import date

from shifu.intelligence.core.domain.enums.ai_quota_status import AiQuotaStatus
from shifu.shared.core.domain.structures import structure


@structure
class AiQuotaUsage:
    percentage: int
    status: AiQuotaStatus
    renews_on: date

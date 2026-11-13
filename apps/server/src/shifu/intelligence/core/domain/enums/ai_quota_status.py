from enum import StrEnum


class AiQuotaStatus(StrEnum):
    NORMAL = 'normal'
    NEAR_LIMIT = 'near_limit'
    BLOCKED = 'blocked'

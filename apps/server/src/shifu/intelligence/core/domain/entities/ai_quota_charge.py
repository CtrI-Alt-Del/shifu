from datetime import date, datetime

from shifu.intelligence.core.domain.enums.ai_quota_request_kind import (
    AiQuotaRequestKind,
)
from shifu.shared.core.domain.entities import entity


@entity
class AiQuotaCharge:
    """One AI request that may spend quota; it makes reports idempotent."""

    request_kind: AiQuotaRequestKind
    request_id: str
    account_id: str
    month: date
    charged_units: int
    refunded: bool
    created_at: datetime
    updated_at: datetime

    @property
    def id(self) -> str:
        return f'{self.request_kind.value}:{self.request_id}'

    @classmethod
    def create(
        cls,
        kind: AiQuotaRequestKind,
        request_id: str,
        account_id: str,
        month: date,
        now: datetime,
    ) -> 'AiQuotaCharge':
        if not request_id or not account_id or month.day != 1:
            raise ValueError('Invalid AI quota charge')
        if now.tzinfo is None:
            raise ValueError('Invalid AI quota charge timestamps')
        return cls(
            request_kind=kind,
            request_id=request_id,
            account_id=account_id,
            month=month,
            charged_units=0,
            refunded=False,
            created_at=now,
            updated_at=now,
        )

    def charge_up_to(self, total_units: int, now: datetime) -> int:
        """Raise the charged total to `total_units` and return the positive difference."""
        if self.refunded or total_units <= self.charged_units:
            return 0
        difference = total_units - self.charged_units
        self.charged_units = total_units
        self.updated_at = now
        return difference

    def refund(self, now: datetime) -> int:
        """Mark the request refunded and return the units the month must give back."""
        if self.refunded:
            return 0
        refunded_units = self.charged_units
        self.refunded = True
        self.updated_at = now
        return refunded_units

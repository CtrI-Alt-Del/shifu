from datetime import date, datetime

from shifu.shared.core.domain.entities import entity


@entity
class AiQuotaMonth:
    """Units an account used in one São Paulo calendar month, with the limit copied at birth."""

    account_id: str
    month: date
    used_units: int
    limit_units: int
    created_at: datetime
    updated_at: datetime

    @property
    def id(self) -> str:
        return f'{self.account_id}:{self.month.isoformat()}'

    @classmethod
    def create(
        cls, account_id: str, month: date, limit_units: int, now: datetime
    ) -> 'AiQuotaMonth':
        if not account_id or month.day != 1 or limit_units <= 0:
            raise ValueError('Invalid AI quota month')
        if now.tzinfo is None:
            raise ValueError('Invalid AI quota month timestamps')
        return cls(
            account_id=account_id,
            month=month,
            used_units=0,
            limit_units=limit_units,
            created_at=now,
            updated_at=now,
        )

    @property
    def is_exhausted(self) -> bool:
        return self.used_units >= self.limit_units

    def add(self, units: int, now: datetime) -> None:
        if units < 0:
            raise ValueError('Quota units to add cannot be negative')
        self.used_units += units
        self.updated_at = now

    def subtract(self, units: int, now: datetime) -> None:
        if units < 0:
            raise ValueError('Quota units to subtract cannot be negative')
        self.used_units = max(self.used_units - units, 0)
        self.updated_at = now

from datetime import date, datetime
from typing import Protocol


class AiQuotaCalendarProvider(Protocol):
    def month_of(self, instant: datetime) -> date:
        """First day of the São Paulo calendar month that contains the instant."""
        ...

    def renewal_of(self, month: date) -> date:
        """First day of the month after the given month."""
        ...

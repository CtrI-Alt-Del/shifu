from datetime import date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo


class ZoneinfoAiQuotaCalendarProvider:
    """Maps instants to the America/Sao_Paulo calendar month used by the AI quota."""

    _ZONE: ClassVar[ZoneInfo] = ZoneInfo('America/Sao_Paulo')

    def month_of(self, instant: datetime) -> date:
        if instant.tzinfo is None:
            raise ValueError('The AI quota calendar needs a timezone-aware instant')
        local = instant.astimezone(self._ZONE)
        return date(local.year, local.month, 1)

    def renewal_of(self, month: date) -> date:
        if month.month == 12:
            return date(month.year + 1, 1, 1)
        return date(month.year, month.month + 1, 1)

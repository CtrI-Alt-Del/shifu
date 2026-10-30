from typing import Protocol


class AccountTimeZoneProvider(Protocol):
    def find_time_zone(self, account_id: str) -> str | None: ...

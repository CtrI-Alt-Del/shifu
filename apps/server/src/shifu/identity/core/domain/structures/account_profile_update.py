from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from shifu.identity.core.domain.errors import (
    InvalidDisplayNameError,
    InvalidTimeZoneError,
)
from shifu.shared.core.domain.structures import structure


@structure
class AccountProfileUpdate:
    display_name: str
    time_zone: str

    def __post_init__(self) -> None:
        name = self.display_name.strip()
        if not name:
            raise InvalidDisplayNameError
        if len(name) > 160:
            raise InvalidDisplayNameError('O nome deve ter no máximo 160 caracteres.')
        object.__setattr__(self, 'display_name', name)
        if not self.time_zone or len(self.time_zone) > 64:
            raise InvalidTimeZoneError
        try:
            ZoneInfo(self.time_zone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise InvalidTimeZoneError from error

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.entities import frozen_entity
from shifu.shared.core.domain.structures import ChronologicalPeriod, NonEmptyText


def _local_date(practiced_at: datetime, time_zone: str) -> date:
    try:
        return practiced_at.astimezone(ZoneInfo(time_zone)).date()
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise InvalidGamificationError from error


@frozen_entity
class PracticeDay:
    id: str
    account_id: str
    practice_date: date
    time_zone: str
    practiced_at: datetime
    recognized_at: datetime

    def __post_init__(self) -> None:
        for value in (self.id, self.account_id, self.time_zone):
            NonEmptyText.create(value, error_type=InvalidGamificationError)
        ChronologicalPeriod.create(
            self.practiced_at, self.recognized_at, error_type=InvalidGamificationError
        )
        if self.practice_date != _local_date(self.practiced_at, self.time_zone):
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        time_zone: str,
        practiced_at: datetime,
        recognized_at: datetime,
    ) -> 'PracticeDay':
        ChronologicalPeriod.create(
            practiced_at, recognized_at, error_type=InvalidGamificationError
        )
        zone = NonEmptyText.create(time_zone, error_type=InvalidGamificationError).value
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            practice_date=_local_date(practiced_at, zone),
            time_zone=zone,
            practiced_at=practiced_at,
            recognized_at=recognized_at,
        )

from datetime import datetime

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.entities import frozen_entity
from shifu.shared.core.domain.structures import (
    AwareTimestamp,
    BoundedInteger,
    ChronologicalPeriod,
    NonEmptyText,
)


@frozen_entity
class ActivityXpRecognition:
    id: str
    account_id: str
    activity_id: str
    attempt_id: str
    granted_xp: int
    xp_grant_id: str | None
    occurred_at: datetime
    recognized_at: datetime

    def __post_init__(self) -> None:
        for value in (self.id, self.account_id, self.activity_id, self.attempt_id):
            NonEmptyText.create(value, error_type=InvalidGamificationError)
        BoundedInteger.create(self.granted_xp, error_type=InvalidGamificationError)
        AwareTimestamp.create(self.occurred_at, error_type=InvalidGamificationError)
        AwareTimestamp.create(self.recognized_at, error_type=InvalidGamificationError)
        ChronologicalPeriod.create(
            self.occurred_at,
            self.recognized_at,
            error_type=InvalidGamificationError,
        )
        if self.xp_grant_id is not None:
            NonEmptyText.create(self.xp_grant_id, error_type=InvalidGamificationError)
        if (self.granted_xp == 0) != (self.xp_grant_id is None):
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        activity_id: str,
        attempt_id: str,
        granted_xp: int,
        xp_grant_id: str | None,
        occurred_at: datetime,
        recognized_at: datetime,
    ) -> 'ActivityXpRecognition':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            activity_id=NonEmptyText.create(
                activity_id, error_type=InvalidGamificationError
            ).value,
            attempt_id=NonEmptyText.create(
                attempt_id, error_type=InvalidGamificationError
            ).value,
            granted_xp=granted_xp,
            xp_grant_id=xp_grant_id,
            occurred_at=occurred_at,
            recognized_at=recognized_at,
        )

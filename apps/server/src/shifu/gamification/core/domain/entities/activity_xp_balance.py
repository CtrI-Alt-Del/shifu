from datetime import datetime
from decimal import Decimal

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import (
    AwareTimestamp,
    BoundedInteger,
    ChronologicalPeriod,
    NonEmptyText,
)


@entity
class ActivityXpBalance:
    id: str
    account_id: str
    activity_id: str
    maximum_xp: int
    granted_xp: int
    updated_at: datetime

    def __post_init__(self) -> None:
        for value in (self.id, self.account_id, self.activity_id):
            NonEmptyText.create(value, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.maximum_xp, minimum=1, error_type=InvalidGamificationError
        )
        BoundedInteger.create(self.granted_xp, error_type=InvalidGamificationError)
        AwareTimestamp.create(self.updated_at, error_type=InvalidGamificationError)

        if self.maximum_xp not in {10, 20, 30} or self.granted_xp > self.maximum_xp:
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        activity_id: str,
        maximum_xp: int,
        created_at: datetime,
    ) -> 'ActivityXpBalance':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            activity_id=NonEmptyText.create(
                activity_id, error_type=InvalidGamificationError
            ).value,
            maximum_xp=maximum_xp,
            granted_xp=0,
            updated_at=created_at,
        )

    def additional_xp_for(self, score: Decimal) -> int:
        if (
            type(score) is not Decimal
            or not score.is_finite()
            or not Decimal(0) <= score <= Decimal(100)
        ):
            raise InvalidGamificationError

        numerator, denominator = score.as_integer_ratio()
        corresponding = self.maximum_xp * numerator // (100 * denominator)
        return max(0, corresponding - self.granted_xp)

    def recognize_score(self, score: Decimal, *, recognized_at: datetime) -> int:
        """Return only the additional XP; persistence and deduplication are external."""
        ChronologicalPeriod.create(
            self.updated_at, recognized_at, error_type=InvalidGamificationError
        )
        additional = self.additional_xp_for(score)
        self.granted_xp += additional
        self.updated_at = recognized_at
        return additional

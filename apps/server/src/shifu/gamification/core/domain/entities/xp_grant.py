from datetime import datetime

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.structures.xp_origin import XpOrigin
from shifu.shared.core.domain.entities import frozen_entity
from shifu.shared.core.domain.structures import (
    BoundedInteger,
    ChronologicalPeriod,
    NonEmptyText,
)


@frozen_entity
class XpGrant:
    id: str
    account_id: str
    fact_id: str
    amount: int
    origin: XpOrigin
    occurred_at: datetime
    granted_at: datetime

    def __post_init__(self) -> None:
        for value in (self.id, self.account_id, self.fact_id):
            NonEmptyText.create(value, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.amount, minimum=1, error_type=InvalidGamificationError
        )
        ChronologicalPeriod.create(
            self.occurred_at, self.granted_at, error_type=InvalidGamificationError
        )
        if type(self.origin) is not XpOrigin:
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        fact_id: str,
        amount: int,
        origin: XpOrigin,
        occurred_at: datetime,
        granted_at: datetime,
    ) -> 'XpGrant':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            fact_id=NonEmptyText.create(
                fact_id, error_type=InvalidGamificationError
            ).value,
            amount=amount,
            origin=origin,
            occurred_at=occurred_at,
            granted_at=granted_at,
        )

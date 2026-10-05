from datetime import datetime

from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import (
    AwareTimestamp,
    BoundedInteger,
    ChronologicalPeriod,
    NonEmptyText,
)


@entity
class RewardFeedback:
    id: str
    account_id: str
    fact_id: str
    xp_grant_ids: tuple[str, ...]
    earned_achievement_ids: tuple[str, ...]
    previous_level: int
    new_level: int
    created_at: datetime
    seen_at: datetime | None = None

    def __post_init__(self) -> None:
        for value in (self.id, self.account_id, self.fact_id):
            NonEmptyText.create(value, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.previous_level, minimum=1, error_type=InvalidGamificationError
        )
        BoundedInteger.create(
            self.new_level, minimum=1, error_type=InvalidGamificationError
        )
        AwareTimestamp.create(self.created_at, error_type=InvalidGamificationError)
        for references in (self.xp_grant_ids, self.earned_achievement_ids):
            if type(references) is not tuple:
                raise InvalidGamificationError
            for reference in references:
                NonEmptyText.create(reference, error_type=InvalidGamificationError)
            if len(references) != len(set(references)):
                raise InvalidGamificationError
        if not self.xp_grant_ids or self.new_level < self.previous_level:
            raise InvalidGamificationError
        if self.seen_at is not None:
            ChronologicalPeriod.create(
                self.created_at, self.seen_at, error_type=InvalidGamificationError
            )

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        fact_id: str,
        xp_grant_ids: tuple[str, ...],
        earned_achievement_ids: tuple[str, ...],
        previous_level: int,
        new_level: int,
        created_at: datetime,
    ) -> 'RewardFeedback':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            fact_id=NonEmptyText.create(
                fact_id, error_type=InvalidGamificationError
            ).value,
            xp_grant_ids=xp_grant_ids,
            earned_achievement_ids=earned_achievement_ids,
            previous_level=previous_level,
            new_level=new_level,
            created_at=created_at,
        )

    def mark_seen(self, *, presented_at: datetime) -> None:
        """Only an actual presentation may acknowledge this feedback."""
        ChronologicalPeriod.create(
            self.created_at, presented_at, error_type=InvalidGamificationError
        )
        if self.seen_at is None:
            self.seen_at = presented_at

from datetime import datetime

from shifu.gamification.core.domain.enums.milestone_kind import MilestoneKind
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.entities import frozen_entity
from shifu.shared.core.domain.structures import (
    BoundedInteger,
    ChronologicalPeriod,
    EnumValue,
    NonEmptyText,
)


@frozen_entity
class RewardedMilestone:
    id: str
    account_id: str
    fact_id: str
    kind: MilestoneKind
    subject_id: str
    xp_grant_id: str
    occurred_at: datetime
    rewarded_at: datetime

    def __post_init__(self) -> None:
        for value in (
            self.id,
            self.account_id,
            self.fact_id,
            self.subject_id,
            self.xp_grant_id,
        ):
            NonEmptyText.create(value, error_type=InvalidGamificationError)
        EnumValue.create(self.kind, MilestoneKind, error_type=InvalidGamificationError)
        ChronologicalPeriod.create(
            self.occurred_at, self.rewarded_at, error_type=InvalidGamificationError
        )

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        fact_id: str,
        kind: MilestoneKind,
        subject_id: str,
        xp_grant_id: str,
        occurred_at: datetime,
        rewarded_at: datetime,
    ) -> 'RewardedMilestone':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            fact_id=NonEmptyText.create(
                fact_id, error_type=InvalidGamificationError
            ).value,
            kind=kind,
            subject_id=NonEmptyText.create(
                subject_id, error_type=InvalidGamificationError
            ).value,
            xp_grant_id=NonEmptyText.create(
                xp_grant_id, error_type=InvalidGamificationError
            ).value,
            occurred_at=occurred_at,
            rewarded_at=rewarded_at,
        )

    @staticmethod
    def xp_for(kind: MilestoneKind, *, diagnosed_competencies: int = 0) -> int:
        EnumValue.create(kind, MilestoneKind, error_type=InvalidGamificationError)
        BoundedInteger.create(
            diagnosed_competencies, error_type=InvalidGamificationError
        )
        if kind is MilestoneKind.DIAGNOSIS:
            BoundedInteger.create(
                diagnosed_competencies, minimum=1, error_type=InvalidGamificationError
            )
            return 20 * diagnosed_competencies
        if diagnosed_competencies != 0:
            raise InvalidGamificationError
        return 50 if kind is MilestoneKind.COMPETENCY_MASTERY else 100

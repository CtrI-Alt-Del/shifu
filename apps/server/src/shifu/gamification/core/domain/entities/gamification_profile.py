from datetime import datetime
from math import isqrt
from typing import ClassVar

from shifu.gamification.core.domain.errors import (
    InvalidGamificationError,
    InvalidStreakReminderHourError,
)
from shifu.gamification.core.domain.structures.practice_streak import PracticeStreak
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import (
    AwareTimestamp,
    BoundedInteger,
    ChronologicalPeriod,
    NonEmptyText,
)


@entity
class GamificationProfile:
    REMINDER_HOUR_MIN: ClassVar[int] = 6
    REMINDER_HOUR_MAX: ClassVar[int] = 22
    DEFAULT_REMINDER_HOUR: ClassVar[int] = 18

    id: str
    account_id: str
    total_xp: int
    level: int
    streak: PracticeStreak
    created_at: datetime
    updated_at: datetime
    reminder_hour: int = DEFAULT_REMINDER_HOUR
    reminder_invite_answered_at: datetime | None = None

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidGamificationError)
        NonEmptyText.create(self.account_id, error_type=InvalidGamificationError)
        BoundedInteger.create(self.total_xp, error_type=InvalidGamificationError)
        BoundedInteger.create(
            self.level, minimum=1, error_type=InvalidGamificationError
        )
        ChronologicalPeriod.create(
            self.created_at, self.updated_at, error_type=InvalidGamificationError
        )
        if type(self.streak) is not PracticeStreak:
            raise InvalidGamificationError
        self._require_reminder_hour(self.reminder_hour)
        if self.reminder_invite_answered_at is not None:
            AwareTimestamp.create(
                self.reminder_invite_answered_at, error_type=InvalidGamificationError
            )
        computed_level = self.level_for_xp(self.total_xp)
        if self.level < computed_level:
            raise InvalidGamificationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        created_at: datetime,
    ) -> 'GamificationProfile':
        return cls(
            id=NonEmptyText.create(id, error_type=InvalidGamificationError).value,
            account_id=NonEmptyText.create(
                account_id, error_type=InvalidGamificationError
            ).value,
            total_xp=0,
            level=1,
            streak=PracticeStreak(),
            created_at=created_at,
            updated_at=created_at,
        )

    @staticmethod
    def minimum_xp_for_level(level: int) -> int:
        BoundedInteger.create(level, minimum=1, error_type=InvalidGamificationError)
        return 50 * level * (level - 1)

    @staticmethod
    def level_for_xp(total_xp: int) -> int:
        BoundedInteger.create(total_xp, error_type=InvalidGamificationError)
        return (1 + isqrt(1 + 4 * (total_xp // 50))) // 2

    def add_xp(self, amount: int, *, granted_at: datetime) -> None:
        """Apply a grant already confirmed by the owning use case."""
        BoundedInteger.create(amount, minimum=1, error_type=InvalidGamificationError)
        ChronologicalPeriod.create(
            self.updated_at, granted_at, error_type=InvalidGamificationError
        )
        total = self.total_xp + amount
        level = self.level_for_xp(total)
        self.total_xp = total
        self.level = max(self.level, level)
        self.updated_at = granted_at

    def update_streak(self, streak: PracticeStreak, *, updated_at: datetime) -> None:
        ChronologicalPeriod.create(
            self.updated_at, updated_at, error_type=InvalidGamificationError
        )
        if type(streak) is not PracticeStreak or streak.longest < self.streak.longest:
            raise InvalidGamificationError
        if self.streak.latest_practice_date is not None and (
            streak.latest_practice_date is None
            or streak.latest_practice_date < self.streak.latest_practice_date
        ):
            raise InvalidGamificationError
        self.streak = streak
        self.updated_at = updated_at

    def change_reminder_hour(self, hour: int, *, updated_at: datetime) -> None:
        self._require_reminder_hour(hour)
        AwareTimestamp.create(updated_at, error_type=InvalidGamificationError)
        self.reminder_hour = hour
        self.updated_at = max(self.updated_at, updated_at)

    def answer_reminder_invite(self, *, answered_at: datetime) -> None:
        """Record the learner's first answer to the reminder invite.

        A later answer changes nothing, so a repeated call keeps the original
        instant.
        """
        AwareTimestamp.create(answered_at, error_type=InvalidGamificationError)
        if self.reminder_invite_answered_at is not None:
            return
        self.reminder_invite_answered_at = answered_at
        self.updated_at = max(self.updated_at, answered_at)

    @classmethod
    def _require_reminder_hour(cls, hour: int) -> None:
        BoundedInteger.create(
            hour,
            minimum=cls.REMINDER_HOUR_MIN,
            maximum=cls.REMINDER_HOUR_MAX,
            error_type=InvalidStreakReminderHourError,
        )

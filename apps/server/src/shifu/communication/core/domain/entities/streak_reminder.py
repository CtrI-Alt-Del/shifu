from datetime import date, datetime

from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.core.domain.errors import (
    CommunicationTransitionError,
    InvalidCommunicationError,
)
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class StreakReminder:
    id: str
    account_id: str
    local_date: date
    streak_days: int
    status: StreakReminderStatus
    expires_at: datetime
    attempt_count: int
    next_attempt_at: datetime | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidCommunicationError)
        NonEmptyText.create(self.account_id, error_type=InvalidCommunicationError)
        try:
            self.status = StreakReminderStatus(self.status)
        except ValueError:
            raise InvalidCommunicationError from None
        if self.streak_days < 1 or self.attempt_count < 0:
            raise InvalidCommunicationError
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise InvalidCommunicationError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        local_date: date,
        streak_days: int,
        expires_at: datetime,
        now: datetime,
    ) -> 'StreakReminder':
        return cls(
            id=id,
            account_id=account_id,
            local_date=local_date,
            streak_days=streak_days,
            status=StreakReminderStatus.PENDING,
            expires_at=expires_at,
            attempt_count=0,
            next_attempt_at=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status is not StreakReminderStatus.PENDING

    def start_attempt(self, now: datetime) -> None:
        self._require_pending()
        self.attempt_count += 1
        self.next_attempt_at = None
        self.updated_at = now

    def schedule_retry(self, next_attempt_at: datetime, now: datetime) -> None:
        self._require_pending()
        if next_attempt_at.tzinfo is None or next_attempt_at.utcoffset() is None:
            raise InvalidCommunicationError
        if next_attempt_at >= self.expires_at:
            raise InvalidCommunicationError
        self.next_attempt_at = next_attempt_at
        self.updated_at = now

    def skip(self, now: datetime) -> None:
        self._finish(StreakReminderStatus.SKIPPED, now)

    def mark_sent(self, now: datetime) -> None:
        self._finish(StreakReminderStatus.SENT, now)

    def mark_failed(self, now: datetime) -> None:
        self._finish(StreakReminderStatus.FAILED, now)

    def expire(self, now: datetime) -> None:
        self._finish(StreakReminderStatus.EXPIRED, now)

    def cancel(self, now: datetime) -> None:
        self._finish(StreakReminderStatus.CANCELLED, now)

    def _finish(self, status: StreakReminderStatus, now: datetime) -> None:
        self._require_pending()
        self.status = status
        self.next_attempt_at = None
        self.completed_at = now
        self.updated_at = now

    def _require_pending(self) -> None:
        if self.status is not StreakReminderStatus.PENDING:
            raise CommunicationTransitionError

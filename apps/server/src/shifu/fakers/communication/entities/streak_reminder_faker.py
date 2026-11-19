from datetime import UTC, date, datetime, timedelta
from typing import ClassVar

from shifu.communication.core.domain.entities import StreakReminder
from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.fakers.shared.id_provider_faker import IdProviderFaker


class StreakReminderFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        local_date: date | None = None,
        streak_days: int = 7,
        status: StreakReminderStatus = StreakReminderStatus.PENDING,
        expires_at: datetime | None = None,
        attempt_count: int = 0,
        next_attempt_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> StreakReminder:
        created = created_at or datetime.now(UTC)
        return StreakReminder(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=(
                account_id if account_id is not None else cls._id_provider.generate()
            ),
            local_date=local_date or created.date(),
            streak_days=streak_days,
            status=status,
            expires_at=expires_at or created + timedelta(hours=6),
            attempt_count=attempt_count,
            next_attempt_at=next_attempt_at,
            created_at=created,
            updated_at=updated_at or created,
            completed_at=completed_at,
        )

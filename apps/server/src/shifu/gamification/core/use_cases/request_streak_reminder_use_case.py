from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from shifu.gamification.core.domain.current_practice_run import current_practice_run
from shifu.gamification.core.domain.events import (
    StreakReminderRequestedEvent,
    StreakReminderRequestedPayload,
)
from shifu.gamification.core.domain.reminder_slot_start import (
    require_reminder_slot_start,
)
from shifu.shared.core.domain.resolved_time_zone import resolved_time_zone
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.shared.core.interfaces import ActiveAccountProvider


class RequestStreakReminderUseCase:
    """Re-check every rule for one due learner and request the reminder.

    The check runs against the slot, never against the execution clock, so a
    retry evaluates the same slot. The request changes no Gamification state:
    it grants no XP and touches no streak, calendar or achievement. It returns
    `True` only when a requested event was recorded.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        active_account_provider: ActiveAccountProvider,
    ) -> None:
        self._database = database
        self._active_account_provider = active_account_provider

    def execute(
        self, account_id: str, *, slot_start: datetime, ignore_hour: bool = False
    ) -> bool:
        slot = require_reminder_slot_start(slot_start)

        accounts = self._active_account_provider.find_many_active([account_id])
        account = next(
            (item for item in accounts if item.account_id == account_id), None
        )
        if account is None:
            return False

        zone = ZoneInfo(resolved_time_zone(account.time_zone))
        local = slot.astimezone(zone)
        local_date = local.date()

        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                return False
            if not ignore_hour and (
                local.hour != profile.reminder_hour or local.minute != 0
            ):
                return False

            dates = tuple(
                sorted(
                    set(
                        repositories.practice_days.find_many_dates_by_account_id(
                            account_id
                        )
                    )
                )
            )
            if local_date in dates:
                return False
            run = current_practice_run(dates, today=local_date)
            if len(run) < 1:
                return False

            next_day_start = datetime.combine(
                local_date + timedelta(days=1), time.min, tzinfo=zone
            ).astimezone(UTC)
            repositories.events.add(
                StreakReminderRequestedEvent(
                    payload=StreakReminderRequestedPayload(
                        account_id=account_id,
                        local_date=local_date.isoformat(),
                        streak_days=len(run),
                        expires_at=next_day_start.isoformat().replace('+00:00', 'Z'),
                    )
                )
            )
            return True

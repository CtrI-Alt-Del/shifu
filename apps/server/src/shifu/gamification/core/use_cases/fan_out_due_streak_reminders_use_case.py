from datetime import datetime, timedelta
from typing import ClassVar
from zoneinfo import ZoneInfo

from shifu.gamification.core.domain.events import (
    StreakReminderDueEvent,
    StreakReminderDuePayload,
)
from shifu.gamification.core.domain.reminder_slot_start import (
    SLOT_MINUTES,
    require_reminder_slot_start,
)
from shifu.gamification.core.domain.resolved_time_zone import resolved_time_zone
from shifu.gamification.core.domain.structures import StreakReminderFanOutPage
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.shared.core.interfaces import ActiveAccountProvider


class FanOutDueStreakRemindersUseCase:
    """Record one due event per learner whose reminder hour starts at this slot.

    Each call handles one bounded page of candidates, so a durable job can run
    one step per page and a retried step repeats only its own page. A learner
    is due only when the slot's local time is exactly `reminder_hour:00` in the
    learner's current zone. A learner who has not practiced for more than two
    UTC days cannot hold a streak through their local yesterday, so only recent
    practitioners are candidates.
    """

    SLOT_MINUTES: ClassVar[int] = SLOT_MINUTES
    CANDIDATE_LOOKBACK_DAYS: ClassVar[int] = 2
    PAGE_SIZE: ClassVar[int] = 200

    def __init__(
        self,
        database: GamificationDatabase,
        active_account_provider: ActiveAccountProvider,
    ) -> None:
        self._database = database
        self._active_account_provider = active_account_provider

    def execute(
        self, slot_start: datetime, *, after_account_id: str | None = None
    ) -> StreakReminderFanOutPage:
        slot = require_reminder_slot_start(slot_start)
        practiced_since = slot.date() - timedelta(days=self.CANDIDATE_LOOKBACK_DAYS)

        with self._database.transaction() as repositories:
            candidates = repositories.profiles.find_many_reminder_candidates(
                practiced_since=practiced_since,
                after_account_id=after_account_id,
                limit=self.PAGE_SIZE,
            )
        if not candidates:
            return StreakReminderFanOutPage(due_count=0, next_cursor=None)

        accounts = {
            account.account_id: account
            for account in self._active_account_provider.find_many_active(
                [profile.account_id for profile in candidates]
            )
        }

        due_events: list[StreakReminderDueEvent] = []
        for profile in candidates:
            account = accounts.get(profile.account_id)
            if account is None:
                continue
            local = slot.astimezone(ZoneInfo(resolved_time_zone(account.time_zone)))
            if local.hour != profile.reminder_hour or local.minute != 0:
                continue
            due_events.append(
                StreakReminderDueEvent(
                    payload=StreakReminderDuePayload(
                        account_id=profile.account_id,
                        local_date=local.date().isoformat(),
                        slot_start=slot.isoformat().replace('+00:00', 'Z'),
                    )
                )
            )

        if due_events:
            with self._database.transaction() as repositories:
                for event in due_events:
                    repositories.events.add(event)

        next_cursor = (
            candidates[-1].account_id if len(candidates) >= self.PAGE_SIZE else None
        )
        return StreakReminderFanOutPage(
            due_count=len(due_events), next_cursor=next_cursor
        )

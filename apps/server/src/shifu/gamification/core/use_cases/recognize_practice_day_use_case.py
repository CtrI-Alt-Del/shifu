from datetime import date, datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.shared.core.interfaces import IdentifierProvider

_FALLBACK_TIME_ZONE = 'UTC'


def _resolve_time_zone(time_zone: str | None) -> str:
    """Resolve the submission zone, falling back to UTC.

    An absent, empty or unresolvable identifier must never cost the learner a
    practice day: `PracticeDay` rejects an unknown zone, and inside a job that
    rejection is retriable and would dead-letter the fact after its retries.
    """
    if not time_zone:
        return _FALLBACK_TIME_ZONE
    try:
        ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError):
        return _FALLBACK_TIME_ZONE
    return time_zone


def _streak_from_dates(dates: tuple[date, ...], *, today: date) -> PracticeStreak:
    ordered = sorted(set(dates))
    if not ordered:
        return PracticeStreak()

    longest = 1
    run = 1
    for previous, following in pairwise(ordered):
        run = run + 1 if (following - previous).days == 1 else 1
        longest = max(longest, run)

    latest = ordered[-1]
    current = 0
    if latest in (today, today - timedelta(days=1)):
        current = 1
        index = len(ordered) - 1
        while index > 0 and (ordered[index] - ordered[index - 1]).days == 1:
            current += 1
            index -= 1

    return PracticeStreak(current=current, longest=longest, latest_practice_date=latest)


class RecognizePracticeDayUseCase:
    """Recognize one practice day from a confirmed Learning fact.

    The day is dated in the time zone that was in effect at submission, and
    the streak is recomputed from the complete practice-day set rather than
    incremented, so a late evaluation filling an older gap corrects both the
    current and the longest streak with no special path.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        identifier_provider: IdentifierProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider

    def execute(
        self,
        account_id: str,
        *,
        practiced_at: datetime,
        time_zone: str | None,
        now: datetime,
    ) -> None:
        zone = _resolve_time_zone(time_zone)

        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                return

            practice_day = PracticeDay.create(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                time_zone=zone,
                practiced_at=practiced_at,
                recognized_at=now,
            )
            if not repositories.practice_days.try_add(practice_day):
                return

            dates = repositories.practice_days.find_many_dates_by_account_id(account_id)
            today = now.astimezone(ZoneInfo(zone)).date()
            profile.update_streak(
                _streak_from_dates(dates, today=today), updated_at=now
            )
            repositories.profiles.update(profile)

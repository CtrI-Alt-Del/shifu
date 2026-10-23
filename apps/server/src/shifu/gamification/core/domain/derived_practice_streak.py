from datetime import date
from itertools import pairwise

from shifu.gamification.core.domain.structures.practice_streak import PracticeStreak


def _longest_run(ordered_dates: tuple[date, ...]) -> int:
    if not ordered_dates:
        return 0
    longest = 1
    run = 1
    for previous, following in pairwise(ordered_dates):
        run = run + 1 if (following - previous).days == 1 else 1
        longest = max(longest, run)
    return longest


def derived_practice_streak(
    stored: PracticeStreak,
    *,
    ordered_dates: tuple[date, ...],
    current_run: tuple[date, ...],
) -> PracticeStreak:
    """The streak a viewer sees now: current decays with time, longest ratchets.

    `current` is derived against the viewer's today rather than read from the
    stored snapshot, because a streak decays with the passage of time and no
    stored column can stay correct without a write. `longest` stays the stored
    fact, but can never fall below what the recorded days already prove — a
    profile whose snapshot was never written would otherwise report longest 0
    beside a real latest date, which `PracticeStreak` rejects.

    Shared by the practice calendar and the overview so the two surfaces cannot
    report different streaks for the same account and instant.
    """
    if not ordered_dates:
        return PracticeStreak(
            current=0,
            longest=stored.longest,
            latest_practice_date=stored.latest_practice_date,
        )
    return PracticeStreak(
        current=len(current_run),
        longest=max(stored.longest, _longest_run(ordered_dates)),
        latest_practice_date=ordered_dates[-1],
    )

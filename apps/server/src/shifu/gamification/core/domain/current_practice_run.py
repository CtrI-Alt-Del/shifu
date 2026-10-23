from datetime import date, timedelta


def current_practice_run(
    ordered_dates: tuple[date, ...], *, today: date
) -> tuple[date, ...]:
    """The consecutive run ending today or yesterday, empty when broken.

    A run held through yesterday is still active during today, so the learner
    keeps their streak while the day is unfinished.
    """
    if not ordered_dates:
        return ()
    latest = ordered_dates[-1]
    if latest not in (today, today - timedelta(days=1)):
        return ()
    index = len(ordered_dates) - 1
    while index > 0 and (ordered_dates[index] - ordered_dates[index - 1]).days == 1:
        index -= 1
    return ordered_dates[index:]

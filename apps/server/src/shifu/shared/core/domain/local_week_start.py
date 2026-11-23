from datetime import date, timedelta


def local_week_start(day: date) -> date:
    """Monday of the Monday-to-Sunday week that contains ``day``.

    Shared by the Learning panorama and the Gamification overview so both
    group a learner's local dates into the same weeks.
    """
    return day - timedelta(days=day.weekday())

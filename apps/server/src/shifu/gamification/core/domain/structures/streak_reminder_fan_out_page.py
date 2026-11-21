from shifu.shared.core.domain.structures import structure


@structure
class StreakReminderFanOutPage:
    due_count: int
    next_cursor: str | None

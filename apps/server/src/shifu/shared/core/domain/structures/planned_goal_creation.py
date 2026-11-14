from shifu.shared.core.domain.structures.structure import structure


@structure
class PlannedGoalCreation:
    """The Goal Learning created (or already had) for one confirmation."""

    goal_id: str
    confirmation_key: str
    replayed: bool

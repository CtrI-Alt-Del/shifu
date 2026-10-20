from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class GoalConfirmation:
    """The durable record of one confirmed Planner proposal turned into a Goal.

    It outlives the temporary planning, so a repeated confirmation finds the same
    Goal instead of creating another one.
    """

    account_id: str
    confirmation_key: str
    planning_id: str
    goal_id: str
    fingerprint: str
    created_at: datetime

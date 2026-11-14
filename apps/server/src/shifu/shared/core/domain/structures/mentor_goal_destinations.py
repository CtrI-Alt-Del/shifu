from shifu.shared.core.domain.structures.mentor_goal_destination import (
    MentorGoalDestination,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class MentorGoalDestinations:
    goals: tuple[MentorGoalDestination, ...]

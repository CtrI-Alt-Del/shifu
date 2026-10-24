from shifu.shared.core.domain.structures.planned_goal_skill import PlannedGoalSkill
from shifu.shared.core.domain.structures.structure import structure


@structure
class PlannedGoalConfirmation:
    """A proposal the learner confirmed, handed from Intelligence to Learning.

    The confirmation key identifies one confirmation across retries, so the same
    key never creates a second Goal.
    """

    account_id: str
    confirmation_key: str
    planning_id: str
    title: str
    description: str
    skills: tuple[PlannedGoalSkill, ...]

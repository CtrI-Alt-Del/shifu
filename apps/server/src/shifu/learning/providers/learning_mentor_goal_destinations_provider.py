from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import (
    MentorGoalDestination,
    MentorGoalDestinations,
)


class LearningMentorGoalDestinationsProvider:
    """Read-only projection of the learner's Objectives for Mentor proposals.

    It authorizes nothing: Learning revalidates when a confirmation executes.
    """

    def __init__(self, database: LearningDatabase) -> None:
        self._database = database

    def read(self, account_id: str, skill_id: str) -> MentorGoalDestinations:
        with self._database.transaction() as repositories:
            goals = sorted(
                repositories.goals.find_many_by_account_id(account_id),
                key=lambda goal: (goal.created_at, goal.id),
            )
            destinations: list[MentorGoalDestination] = []
            for goal in goals:
                experience = (
                    repositories.skill_experiences.find_by_goal_id_and_skill_id(
                        goal.id, skill_id
                    )
                )
                destinations.append(
                    MentorGoalDestination(
                        goal_id=goal.id,
                        title=goal.title,
                        skill_experience_id=(
                            experience.id if experience is not None else None
                        ),
                    )
                )
        return MentorGoalDestinations(goals=tuple(destinations))

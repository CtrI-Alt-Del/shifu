from typing import Protocol

from shifu.shared.core.domain.structures import (
    PlannedGoalConfirmation,
    PlannedGoalCreation,
)


class PlannedGoalProvider(Protocol):
    """Learning's side of a confirmed Planner proposal.

    `create` validates Learning's own rules and creates the Goal with every Skill
    as one result; repeating the same confirmation key returns the same Goal.
    `find` recovers a completed confirmation after the temporary planning is gone.
    """

    def create(self, confirmation: PlannedGoalConfirmation) -> PlannedGoalCreation: ...

    def find(
        self, account_id: str, confirmation_key: str
    ) -> PlannedGoalCreation | None: ...

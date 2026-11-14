from shifu.intelligence.core.domain.enums import PlanningSessionStatus
from shifu.intelligence.core.domain.errors import (
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.shared.core.domain.structures import (
    PlannedGoalConfirmation,
    PlannedGoalCreation,
    PlannedGoalSkill,
)
from shifu.shared.core.interfaces import PlannedGoalProvider


class ConfirmPlanningUseCase:
    """Hand the active proposal, with the learner's edits, to Learning.

    The Skills and their justifications always come from the stored proposal, never
    from the client. A completed confirmation stays recoverable by its key after the
    temporary planning is discarded.
    """

    def __init__(
        self,
        sessions: PlanningSessionsRepository,
        planned_goals: PlannedGoalProvider,
    ) -> None:
        self._sessions = sessions
        self._planned_goals = planned_goals

    def execute(
        self,
        account_id: str,
        planning_id: str,
        confirmation_key: str,
        title: str,
        description: str,
    ) -> PlannedGoalCreation:
        session = self._sessions.find_by_id(planning_id)
        if session is None or session.account_id != account_id:
            recovered = self._planned_goals.find(account_id, confirmation_key)
            if recovered is None:
                raise PlanningSessionNotFoundError
            return recovered
        if session.operation is not None:
            raise PlanningOperationConflictError
        if (
            session.status is not PlanningSessionStatus.PROPOSAL
            or session.proposal is None
        ):
            raise PlanningStateConflictError

        creation = self._planned_goals.create(
            PlannedGoalConfirmation(
                account_id=account_id,
                confirmation_key=confirmation_key,
                planning_id=planning_id,
                title=title,
                description=description,
                skills=tuple(
                    PlannedGoalSkill(
                        skill_id=skill.skill_id, inclusion_reason=skill.justification
                    )
                    for skill in session.proposal.skills
                ),
            )
        )
        # The Goal is Learning's record now; the temporary planning ends here.
        self._sessions.remove(planning_id)
        return creation

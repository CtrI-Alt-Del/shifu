from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.create_planned_goal_use_case import (
    CreatePlannedGoalUseCase,
)
from shifu.shared.core.domain.structures import (
    PlannedGoalConfirmation,
    PlannedGoalCreation,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)


class LearningPlannedGoalProvider:
    """Learning's implementation of the Shared planned-goal port.

    Intelligence hands over a confirmed proposal; Learning keeps the authority on
    validation, creation and recovery of the same confirmation.
    """

    def __init__(
        self,
        database: LearningDatabase,
        curriculum: CurriculumContentProvider,
        clock: ClockProvider,
        identifiers: IdentifierProvider,
        require_ready_skills: bool = True,
    ) -> None:
        self._database = database
        self._create = CreatePlannedGoalUseCase(
            database, curriculum, clock, identifiers, require_ready_skills
        )

    def create(self, confirmation: PlannedGoalConfirmation) -> PlannedGoalCreation:
        return self._create.execute(confirmation)

    def find(
        self, account_id: str, confirmation_key: str
    ) -> PlannedGoalCreation | None:
        with self._database.transaction() as repositories:
            stored = repositories.goal_confirmations.find(account_id, confirmation_key)
        if stored is None:
            return None
        return PlannedGoalCreation(
            goal_id=stored.goal_id,
            confirmation_key=stored.confirmation_key,
            replayed=True,
        )

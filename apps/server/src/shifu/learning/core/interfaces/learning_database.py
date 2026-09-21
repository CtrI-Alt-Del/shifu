from contextlib import AbstractContextManager
from typing import Protocol

from shifu.learning.core.interfaces.activity_attempts_repository import (
    ActivityAttemptsRepository,
)
from shifu.learning.core.interfaces.activity_evaluations_repository import (
    ActivityEvaluationsRepository,
)
from shifu.learning.core.interfaces.competency_progresses_repository import (
    CompetencyProgressesRepository,
)
from shifu.learning.core.interfaces.goals_repository import GoalsRepository
from shifu.learning.core.interfaces.skill_experiences_repository import (
    SkillExperiencesRepository,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class LearningDatabaseRepositories:
    goals: GoalsRepository
    skill_experiences: SkillExperiencesRepository
    competency_progresses: CompetencyProgressesRepository
    activity_attempts: ActivityAttemptsRepository
    activity_evaluations: ActivityEvaluationsRepository
    events: EventsRepository


class LearningDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[LearningDatabaseRepositories]:
        """Open the sole transaction boundary for one Learning operation."""
        ...

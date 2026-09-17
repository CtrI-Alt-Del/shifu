from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.interfaces import (
    ActivityAttemptsRepository,
    ActivityEvaluationsRepository,
    CompetencyProgressesRepository,
    GoalsRepository,
    SkillExperiencesRepository,
)


class LearningSeeder:
    def __init__(
        self,
        goals_repository: GoalsRepository,
        skill_experiences_repository: SkillExperiencesRepository,
        competency_progresses_repository: CompetencyProgressesRepository,
        activity_attempts_repository: ActivityAttemptsRepository,
        activity_evaluations_repository: ActivityEvaluationsRepository,
    ) -> None:
        self._goals_repository = goals_repository
        self._skill_experiences_repository = skill_experiences_repository
        self._competency_progresses_repository = competency_progresses_repository
        self._activity_attempts_repository = activity_attempts_repository
        self._activity_evaluations_repository = activity_evaluations_repository

    def clear(self) -> None:
        self._activity_evaluations_repository.remove_all()
        self._activity_attempts_repository.remove_all()
        self._competency_progresses_repository.remove_all()
        self._skill_experiences_repository.remove_all()
        self._goals_repository.remove_all()

    def run(
        self,
        goals: list[Goal],
        skill_experiences: list[SkillExperience],
        competency_progresses: list[CompetencyProgress],
        activity_attempts: list[ActivityAttempt],
        activity_evaluations: list[ActivityEvaluation],
    ) -> None:
        self._goals_repository.add_many(goals)
        self._skill_experiences_repository.add_many(skill_experiences)
        self._competency_progresses_repository.add_many(competency_progresses)
        self._activity_attempts_repository.add_many(activity_attempts)
        self._activity_evaluations_repository.add_many(activity_evaluations)

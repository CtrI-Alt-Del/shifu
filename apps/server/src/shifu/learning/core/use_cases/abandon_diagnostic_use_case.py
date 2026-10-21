from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.interfaces import ClockProvider


class AbandonDiagnosticUseCase:
    def __init__(self, database: LearningDatabase, clock: ClockProvider) -> None:
        self._database = database
        self._clock = clock

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        diagnostic_run_id: str,
    ) -> None:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError

            locked = repositories.skill_experiences.find_by_id_for_update(experience.id)
            if (
                locked is None
                or locked.goal_id != goal_id
                or locked.skill_id != skill_id
            ):
                raise NotFoundError

            if (
                locked.status is not SkillExperienceStatus.DIAGNOSING
                or locked.diagnostic_run_id != diagnostic_run_id
            ):
                raise ConflictError

            repositories.activity_attempts.remove_diagnostic_by_experience(locked.id)
            locked.diagnostic_run_id = None
            locked.status = SkillExperienceStatus.NOT_STARTED
            locked.updated_at = self._clock.now()
            repositories.skill_experiences.update(locked)

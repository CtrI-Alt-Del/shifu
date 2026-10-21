from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


class StartSkillUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum: CurriculumContentProvider,
        clock: ClockProvider,
    ) -> None:
        self._database = database
        self._curriculum = curriculum
        self._clock = clock

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        entry_key: str,
    ) -> SkillExperience:
        with self._database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if goal is None or goal.account_id != account_id or experience is None:
                raise NotFoundError

            catalog = self._curriculum.get_skill_content(skill_id)
            if catalog is None or catalog.id != skill_id:
                raise NotFoundError

            if not catalog.v2_eligible:
                raise CurriculumGapError

            locked = repositories.skill_experiences.find_by_id_for_update(experience.id)
            if locked is None:
                raise NotFoundError

            if locked.status is SkillExperienceStatus.DIAGNOSING:
                if locked.diagnostic_run_id == entry_key:
                    return locked

                repositories.activity_attempts.remove_diagnostic_by_experience(
                    locked.id
                )
                locked.diagnostic_run_id = entry_key
                locked.updated_at = self._clock.now()
                repositories.skill_experiences.update(locked)
                return locked

            if locked.status is not SkillExperienceStatus.NOT_STARTED:
                raise ConflictError

            now = self._clock.now()
            locked.start_diagnosis(now)
            locked.diagnostic_run_id = entry_key
            repositories.skill_experiences.update(locked)
            return locked

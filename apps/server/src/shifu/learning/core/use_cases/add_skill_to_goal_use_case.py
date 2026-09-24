from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.errors import (
    CurriculumSkillNotFoundError,
    GoalNotFoundError,
    InvalidFoundationSelectionError,
    SkillAlreadyAddedError,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumCatalogProvider,
    IdentifierProvider,
)


class AddSkillToGoalUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_catalog_provider: CurriculumCatalogProvider,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_catalog_provider = curriculum_catalog_provider
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        foundation_skill_ids: list[str],
    ) -> list[SkillExperience]:
        with self._learning_database.transaction() as repos:
            goal = repos.goals.find_by_id(goal_id)
            if goal is None or goal.account_id != account_id:
                raise GoalNotFoundError

        skill = self._curriculum_catalog_provider.find_skill_by_id(skill_id)
        if skill is None:
            raise CurriculumSkillNotFoundError

        direct_foundation_ids = {
            foundation.skill_id
            for foundation in self._curriculum_catalog_provider.find_direct_foundations_for_many(
                [skill_id]
            ).get(skill_id, [])
        }
        for foundation_id in foundation_skill_ids:
            if foundation_id not in direct_foundation_ids:
                raise InvalidFoundationSelectionError

        with self._learning_database.transaction() as repos:
            existing_experience = repos.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if existing_experience is not None:
                raise SkillAlreadyAddedError

            existing_skill_ids = {
                experience.skill_id
                for experience in repos.skill_experiences.find_many_by_goal_id(goal_id)
            }
            remaining_foundation_ids = [
                foundation_id
                for foundation_id in foundation_skill_ids
                if foundation_id not in existing_skill_ids
            ]

            now = self._clock_provider.now()
            created_experiences = [
                SkillExperience.create(
                    id=self._identifier_provider.generate(),
                    goal_id=goal_id,
                    skill_id=selected_skill_id,
                    inclusion_reason=None,
                    status=SkillExperienceStatus.NOT_STARTED,
                    created_at=now,
                    updated_at=now,
                )
                for selected_skill_id in [skill_id, *remaining_foundation_ids]
            ]

            repos.skill_experiences.add_many(created_experiences)

            return created_experiences

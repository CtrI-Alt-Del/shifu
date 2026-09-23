from datetime import datetime

from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.errors import (
	GoalNotFoundError,
	InvalidGoalError,
	SkillAlreadyAddedError,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.interfaces import CurriculumCatalogReader, IdentifierProvider


class AddSkillToGoalUseCase:
	def __init__(
		self,
		learning_database: LearningDatabase,
		curriculum_catalog_reader: CurriculumCatalogReader,
		identifier_provider: IdentifierProvider,
	) -> None:
		self._learning_database = learning_database
		self._curriculum_catalog_reader = curriculum_catalog_reader
		self._identifier_provider = identifier_provider

	def execute(
		self,
		goal_id: str,
		skill_id: str,
		foundation_skill_ids: list[str] | None = None,
	) -> list[SkillExperience]:
		if foundation_skill_ids is None:
			foundation_skill_ids = []

		with self._learning_database.transaction() as repos:
			goal = repos.goals.find_by_id(goal_id)
			if goal is None:
				raise GoalNotFoundError(message=f"Goal {goal_id} not found")

			existing_experience = repos.skill_experiences.find_by_goal_id_and_skill_id(
				goal_id, skill_id
			)
			if existing_experience is not None:
				raise SkillAlreadyAddedError(
					message=f"Skill {skill_id} already added to goal {goal_id}"
				)

		skill = self._curriculum_catalog_reader.find_skill_by_id(skill_id)
		if skill is None:
			raise InvalidGoalError(message=f"Skill {skill_id} not found")

		skill_foundations = self._curriculum_catalog_reader.find_direct_foundations_for_many(
			[skill_id]
		)
		direct_foundation_ids = {
			f.skill_id for f in skill_foundations.get(skill_id, [])
		}

		for foundation_id in foundation_skill_ids:
			if foundation_id not in direct_foundation_ids:
				raise InvalidGoalError(
					message=f"Foundation {foundation_id} is not a direct foundation of {skill_id}"
				)

		with self._learning_database.transaction() as repos:
			created_experiences = []
			now = datetime.now()
			skill_experience_id = self._identifier_provider.provide()
			skill_experience = SkillExperience.create(
				id=skill_experience_id,
				goal_id=goal_id,
				skill_id=skill_id,
				inclusion_reason=None,
				status=SkillExperienceStatus.NOT_STARTED,
				created_at=now,
				updated_at=now,
			)
			created_experiences.append(skill_experience)

			for foundation_id in foundation_skill_ids:
				foundation_experience_id = self._identifier_provider.provide()
				foundation_experience = SkillExperience.create(
					id=foundation_experience_id,
					goal_id=goal_id,
					skill_id=foundation_id,
					inclusion_reason=None,
					status=SkillExperienceStatus.NOT_STARTED,
					created_at=now,
					updated_at=now,
				)
				created_experiences.append(foundation_experience)

			repos.skill_experiences.add_many(created_experiences)

			return created_experiences

from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.domain.structures import SkillCatalogRow, SuggestedFoundation
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.interfaces import CurriculumCatalogReader


class SearchSkillCatalogUseCase:
	def __init__(
		self,
		learning_database: LearningDatabase,
		curriculum_catalog_reader: CurriculumCatalogReader,
	) -> None:
		self._learning_database = learning_database
		self._curriculum_catalog_reader = curriculum_catalog_reader

	def execute(
		self,
		goal_id: str,
		query: str | None = None,
		cursor: str | None = None,
		limit: int = 20,
	) -> tuple[list[SkillCatalogRow], str | None]:
		with self._learning_database.transaction() as repos:
			goal = repos.goals.find_by_id(goal_id)
			if goal is None:
				raise GoalNotFoundError(message=f"Goal {goal_id} not found")

			skill_experiences_by_skill_id = {
				se.skill_id: se
				for se in repos.skill_experiences.find_many_by_goal_id(goal_id)
			}

		catalog_page = self._curriculum_catalog_reader.search_skills(
			query=query, cursor=cursor, limit=limit
		)

		skill_ids = [entry.id for entry in catalog_page.items]
		skill_foundations_by_skill_id = (
			self._curriculum_catalog_reader.find_direct_foundations_for_many(
				skill_ids
			)
		)

		with self._learning_database.transaction() as repos:
			rows = []
			for entry in catalog_page.items:
				skill_experience = skill_experiences_by_skill_id.get(entry.id)
				already_in_goal = skill_experience is not None

				foundations_list = skill_foundations_by_skill_id.get(entry.id, [])
				suggested_foundations = tuple(
					SuggestedFoundation(
						skill_id=foundation.skill_id,
						name=foundation.name,
						status='present'
						if skill_experiences_by_skill_id.get(foundation.skill_id)
						else 'missing',
					)
					for foundation in foundations_list
				)

				row = SkillCatalogRow(
					id=entry.id,
					name=entry.name,
					description=entry.description,
					already_in_goal=already_in_goal,
					skill_experience_id=skill_experience.id if skill_experience else None,
					foundations=suggested_foundations,
				)
				rows.append(row)

			return rows, catalog_page.next_cursor

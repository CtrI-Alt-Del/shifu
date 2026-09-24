from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.domain.structures import SkillCatalogRow, SuggestedFoundation
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import SkillCatalogEntry, SkillFoundationEntry
from shifu.shared.core.interfaces import CurriculumCatalogProvider


class SearchSkillCatalogUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_catalog_provider: CurriculumCatalogProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_catalog_provider = curriculum_catalog_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[SkillCatalogRow], str | None]:
        with self._learning_database.transaction() as repos:
            goal = repos.goals.find_by_id(goal_id)
            if goal is None or goal.account_id != account_id:
                raise GoalNotFoundError

            skill_experiences_by_skill_id = {
                experience.skill_id: experience
                for experience in repos.skill_experiences.find_many_by_goal_id(goal_id)
            }

        catalog_page = self._curriculum_catalog_provider.search_skills(
            query=query, cursor=cursor, limit=limit
        )

        skill_ids = [entry.id for entry in catalog_page.items]
        foundations_by_skill_id = (
            self._curriculum_catalog_provider.find_direct_foundations_for_many(
                skill_ids
            )
        )

        rows = [
            self._to_row(
                entry,
                foundations_by_skill_id.get(entry.id, []),
                skill_experiences_by_skill_id,
            )
            for entry in catalog_page.items
        ]

        return rows, catalog_page.next_cursor

    def _to_row(
        self,
        entry: SkillCatalogEntry,
        foundations: list[SkillFoundationEntry],
        skill_experiences_by_skill_id: dict[str, SkillExperience],
    ) -> SkillCatalogRow:
        skill_experience = skill_experiences_by_skill_id.get(entry.id)
        suggested_foundations = tuple(
            SuggestedFoundation(
                skill_id=foundation.skill_id,
                name=foundation.name,
                status='present'
                if foundation.skill_id in skill_experiences_by_skill_id
                else 'missing',
            )
            for foundation in foundations
        )
        return SkillCatalogRow(
            id=entry.id,
            name=entry.name,
            description=entry.description,
            already_in_goal=skill_experience is not None,
            skill_experience_id=(
                skill_experience.id if skill_experience is not None else None
            ),
            foundations=suggested_foundations,
        )

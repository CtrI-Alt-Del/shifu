from shifu.curriculum.core.interfaces import CurriculumDatabase
from shifu.shared.core.domain.structures import (
    SkillCatalogEntry,
    SkillCatalogPage,
    SkillFoundationEntry,
)
from shifu.shared.core.interfaces import CurriculumCatalogReader


class CurriculumCatalogReaderProvider(CurriculumCatalogReader):
    def __init__(self, database: CurriculumDatabase) -> None:
        self._database = database

    def search_skills(
        self, *, query: str | None, cursor: str | None, limit: int
    ) -> SkillCatalogPage:
        with self._database.transaction() as repositories:
            skills, next_cursor = repositories.skills.search(
                query=query, cursor=cursor, limit=limit
            )
            entries = tuple(
                SkillCatalogEntry(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                )
                for skill in skills
            )
            return SkillCatalogPage(items=entries, next_cursor=next_cursor)

    def find_skill_by_id(self, skill_id: str) -> SkillCatalogEntry | None:
        with self._database.transaction() as repositories:
            skill = repositories.skills.find_by_id(skill_id)
            if skill is None:
                return None
            return SkillCatalogEntry(
                id=skill.id,
                name=skill.name,
                description=skill.description,
            )

    def find_direct_foundations_for_many(
        self, skill_ids: list[str]
    ) -> dict[str, list[SkillFoundationEntry]]:
        with self._database.transaction() as repositories:
            skill_foundations_by_skill_id = (
                repositories.skill_foundations.find_many_by_skill_ids(skill_ids)
            )
            foundation_skill_ids = tuple(
                {
                    foundation.foundation_skill_id
                    for foundations in skill_foundations_by_skill_id.values()
                    for foundation in foundations
                }
            )
            foundation_skills_by_id = {
                skill.id: skill
                for skill in repositories.skills.find_many_by_ids(foundation_skill_ids)
            }
            result: dict[str, list[SkillFoundationEntry]] = {}
            for skill_id, foundations in skill_foundations_by_skill_id.items():
                result[skill_id] = [
                    SkillFoundationEntry(
                        skill_id=foundation.foundation_skill_id,
                        name=foundation_skills_by_id[
                            foundation.foundation_skill_id
                        ].name,
                    )
                    for foundation in foundations
                    if foundation.foundation_skill_id in foundation_skills_by_id
                ]
            return result

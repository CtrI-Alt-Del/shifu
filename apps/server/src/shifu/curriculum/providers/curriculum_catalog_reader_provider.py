from shifu.curriculum.core.interfaces import SkillFoundationsRepository, SkillsRepository
from shifu.shared.core.domain.structures import (
	SkillCatalogEntry,
	SkillCatalogPage,
	SkillFoundationEntry,
)
from shifu.shared.core.interfaces import CurriculumCatalogReader


class CurriculumCatalogReaderProvider(CurriculumCatalogReader):
	def __init__(
		self,
		skills_repository: SkillsRepository,
		skill_foundations_repository: SkillFoundationsRepository,
	) -> None:
		self._skills_repository = skills_repository
		self._skill_foundations_repository = skill_foundations_repository

	def search_skills(
		self, query: str | None, cursor: str | None, limit: int
	) -> SkillCatalogPage:
		skills, next_cursor = self._skills_repository.search(
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
		skill = self._skills_repository.find_by_id(skill_id)
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
		skill_foundations_by_skill_id = (
			self._skill_foundations_repository.find_many_by_skill_ids(skill_ids)
		)
		result: dict[str, list[SkillFoundationEntry]] = {}
		for skill_id, skill_foundations in skill_foundations_by_skill_id.items():
			result[skill_id] = [
				SkillFoundationEntry(
					skill_id=sf.foundation_skill_id,
					name=sf.foundation_skill_id,
				)
				for sf in skill_foundations
			]
		return result

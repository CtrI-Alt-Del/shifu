from typing import Protocol

from shifu.shared.core.domain.structures import (
    SkillCatalogEntry,
    SkillCatalogPage,
    SkillFoundationEntry,
)


class CurriculumCatalogProvider(Protocol):
    def search_skills(
        self, *, query: str | None, cursor: str | None, limit: int
    ) -> SkillCatalogPage: ...

    def find_skill_by_id(self, skill_id: str) -> SkillCatalogEntry | None: ...

    def list_skills(self) -> tuple[SkillCatalogEntry, ...]:
        """Return every authorized Skill with its name and description."""
        ...

    def find_direct_foundations_for_many(
        self, skill_ids: list[str]
    ) -> dict[str, list[SkillFoundationEntry]]: ...

from shifu.shared.core.domain.structures.skill_catalog_entry import (
    SkillCatalogEntry,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class SkillCatalogPage:
    items: tuple[SkillCatalogEntry, ...]
    next_cursor: str | None

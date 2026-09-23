from typing import Optional

from shifu.shared.core.domain.decorators import structure
from shifu.shared.core.domain.structures.skill_catalog_entry import (
	SkillCatalogEntry,
)


@structure
class SkillCatalogPage:
	items: tuple[SkillCatalogEntry, ...]
	next_cursor: Optional[str]

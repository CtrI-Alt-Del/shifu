from shifu.shared.core.domain.decorators import structure


@structure
class SkillCatalogEntry:
	id: str
	name: str
	description: str

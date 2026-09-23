from shifu.shared.core.domain.structures import structure


@structure
class SuggestedFoundation:
	skill_id: str
	name: str
	status: str


@structure
class SkillCatalogRow:
	id: str
	name: str
	description: str
	already_in_goal: bool
	skill_experience_id: str | None
	foundations: tuple[SuggestedFoundation, ...]

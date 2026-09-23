from shifu.shared.core.domain.decorators import structure


@structure
class SkillFoundationEntry:
	skill_id: str
	name: str

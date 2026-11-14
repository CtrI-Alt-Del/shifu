from shifu.shared.core.domain.structures import structure


@structure
class PlanningSkillRelation:
    skill_id: str
    foundation_skill_id: str

    def __post_init__(self) -> None:
        if not self.skill_id.strip() or not self.foundation_skill_id.strip():
            raise ValueError('A relation needs two Skill identifiers.')
        if self.skill_id == self.foundation_skill_id:
            raise ValueError('A Skill cannot be its own foundation.')

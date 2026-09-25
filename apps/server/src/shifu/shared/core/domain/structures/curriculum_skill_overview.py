from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumSkillOverview:
    skill_id: str
    name: str
    competency_ids: tuple[str, ...]
    foundation_skill_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.competency_ids) != len(set(self.competency_ids)):
            raise ValueError('Curriculum competency identifiers must be unique.')
        if len(self.foundation_skill_ids) != len(set(self.foundation_skill_ids)):
            raise ValueError('Curriculum foundation Skill identifiers must be unique.')

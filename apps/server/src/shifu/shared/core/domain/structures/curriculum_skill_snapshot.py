from shifu.shared.core.domain.structures.curriculum_competency_snapshot import (
    CurriculumCompetencySnapshot,
)
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumSkillSnapshot:
    id: str
    name: str
    competencies: tuple[CurriculumCompetencySnapshot, ...]
    v2_coverage_gaps: tuple[str, ...] = ()

    @property
    def v2_eligible(self) -> bool:
        return not self.v2_coverage_gaps and bool(self.competencies)

    def __post_init__(self) -> None:
        positions = tuple(competency.position for competency in self.competencies)
        identifiers = tuple(competency.id for competency in self.competencies)
        if len(positions) != len(set(positions)):
            raise ValueError('Curriculum competency positions must be unique.')
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Curriculum competency identifiers must be unique.')
        if any(competency.skill_id != self.id for competency in self.competencies):
            raise ValueError('Curriculum competency does not belong to the Skill.')

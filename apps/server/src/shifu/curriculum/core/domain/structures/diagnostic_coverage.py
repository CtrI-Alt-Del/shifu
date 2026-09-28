from shifu.curriculum.core.domain.structures.skill_v2_coverage import v2_coverage_gaps
from shifu.shared.core.domain.structures import CurriculumSkillSnapshot


def diagnostic_coverage_gaps(skill: CurriculumSkillSnapshot) -> tuple[str, ...]:
    """Keep the existing full Curriculum publication gate for diagnosis."""
    return v2_coverage_gaps(skill)

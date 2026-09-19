from collections.abc import Iterable

from shifu.curriculum.core.domain.entities import Competency
from shifu.curriculum.core.domain.errors import InvalidCompetencyError


def create_competencies(
    competencies: Iterable[Competency],
) -> tuple[Competency, ...]:
    result = tuple(competencies)
    keys = tuple((competency.skill_id, competency.position) for competency in result)
    if len(keys) != len(set(keys)):
        raise InvalidCompetencyError
    return result

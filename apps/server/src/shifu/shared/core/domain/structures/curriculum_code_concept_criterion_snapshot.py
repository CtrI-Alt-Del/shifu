from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumCodeLevelObservationSnapshot:
    id: str
    level: int
    evidence: str
    interpretation_limit: str


@structure
class CurriculumCodeInconclusiveObservationSnapshot:
    id: str
    text: str


@structure
class CurriculumCodeConceptCriterionSnapshot:
    concept_id: str
    description: str
    level_observations: tuple[CurriculumCodeLevelObservationSnapshot, ...]
    inconclusive_observation: CurriculumCodeInconclusiveObservationSnapshot

    def __post_init__(self) -> None:
        for value in (self.concept_id, self.description):
            NonEmptyText.create(value, error_type=ValidationError)
        if (
            tuple(sorted(item.level for item in self.level_observations))
            != (0, 25, 50, 75, 100)
            or len({item.id for item in self.level_observations}) != 5
            or self.inconclusive_observation.id
            in {item.id for item in self.level_observations}
        ):
            raise ValidationError

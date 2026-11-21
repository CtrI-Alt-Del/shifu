from decimal import Decimal

from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumPairMatchingConceptCriterionSnapshot:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    full_score: Decimal | None
    partial_score: Decimal | None
    incorrect_score: Decimal | None

    def __post_init__(self) -> None:
        if not all((self.concept_id, self.criterion, self.examples, self.limits)):
            raise ValueError('Curriculum Concept criterion is incomplete.')
        for score in (self.full_score, self.partial_score, self.incorrect_score):
            if score is not None and not Decimal('0') <= score <= Decimal('100'):
                raise ValueError('Curriculum Concept evidence must be in 0-100.')

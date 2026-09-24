from decimal import Decimal

from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumChoiceConceptCriterionSnapshot:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    correct_score: Decimal | None
    incorrect_score: Decimal | None

    def __post_init__(self) -> None:
        if not all((self.concept_id, self.criterion, self.examples, self.limits)):
            raise ValueError('Curriculum Concept criterion is incomplete.')
        for score in (self.correct_score, self.incorrect_score):
            if score is not None and not Decimal('0') <= score <= Decimal('100'):
                raise ValueError('Curriculum Concept evidence must be in 0-100.')

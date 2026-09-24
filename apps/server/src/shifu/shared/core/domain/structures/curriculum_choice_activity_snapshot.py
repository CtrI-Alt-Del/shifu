from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.curriculum_choice_part_snapshot import (
    CurriculumChoicePartSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_choice_question_snapshot import (
    CurriculumChoiceQuestionSnapshot,
)
from decimal import Decimal

from shifu.shared.core.domain.validation import require_non_empty


@structure
class CurriculumChoiceActivitySnapshot:
    id: str
    competency_id: str
    difficulty: str
    title: str
    questions: tuple[CurriculumChoiceQuestionSnapshot, ...]
    parts: tuple[CurriculumChoicePartSnapshot, ...]
    required_concept_ids: tuple[str, ...] = ()
    activity_type: str = 'learning'

    def __post_init__(self) -> None:
        for name in ('id', 'competency_id', 'difficulty', 'title'):
            object.__setattr__(
                self, name, require_non_empty(getattr(self, name), ValidationError)
            )
        weights = tuple(part.weight_percentage for part in self.parts)
        if (
            not weights
            or any(weight < 0 or weight > 100 for weight in weights)
            or sum(weights, start=Decimal('0')) != Decimal('100')
        ):
            raise ValidationError

from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.curriculum_choice_part_snapshot import (
    CurriculumChoicePartSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_choice_question_snapshot import (
    CurriculumChoiceQuestionSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


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
    revision: str | None = None
    diagnostic_revision: str | None = None

    def __post_init__(self) -> None:
        if self.revision is not None:
            NonEmptyText.create(self.revision, error_type=ValidationError)
        if self.diagnostic_revision is not None:
            NonEmptyText.create(self.diagnostic_revision, error_type=ValidationError)
        for name in ('id', 'competency_id', 'difficulty', 'title'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        weights = tuple(part.weight_percentage for part in self.parts)
        if (
            not weights
            or any(weight < 0 or weight > 100 for weight in weights)
            or sum(weights, start=Decimal('0')) != Decimal('100')
        ):
            raise ValidationError

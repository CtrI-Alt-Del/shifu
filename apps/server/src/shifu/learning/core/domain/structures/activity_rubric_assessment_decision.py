from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CodeRubricDecisions,
    NonEmptyText,
    structure,
)

type ActivityRubricKind = Literal['code', 'translation']


@structure
class ActivityRubricAssessmentDecision:
    question_key: str
    rubric_kind: ActivityRubricKind
    decisions: CodeRubricDecisions

    def __post_init__(self) -> None:
        NonEmptyText.create(self.question_key, error_type=ValidationError)
        if self.rubric_kind not in ('code', 'translation'):
            raise ValidationError

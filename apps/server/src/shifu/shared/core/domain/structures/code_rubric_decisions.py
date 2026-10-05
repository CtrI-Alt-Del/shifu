from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

type CodeRubricLevel = Literal[0, 25, 50, 75, 100, 'inconclusive']


@structure
class CodeCriterionDecision:
    key: str
    level: CodeRubricLevel

    def __post_init__(self) -> None:
        NonEmptyText.create(self.key, error_type=ValidationError)
        if self.level not in (0, 25, 50, 75, 100, 'inconclusive'):
            raise ValidationError


@structure
class CodeConceptDecision:
    concept_id: str
    level: CodeRubricLevel

    def __post_init__(self) -> None:
        NonEmptyText.create(self.concept_id, error_type=ValidationError)
        if self.level not in (0, 25, 50, 75, 100, 'inconclusive'):
            raise ValidationError


@structure
class CodeRubricDecisions:
    criterion_levels: tuple[CodeCriterionDecision, ...]
    concept_levels: tuple[CodeConceptDecision, ...]

    def __post_init__(self) -> None:
        if len(self.criterion_levels) != len(
            {item.key for item in self.criterion_levels}
        ) or len(self.concept_levels) != len(
            {item.concept_id for item in self.concept_levels}
        ):
            raise ValidationError

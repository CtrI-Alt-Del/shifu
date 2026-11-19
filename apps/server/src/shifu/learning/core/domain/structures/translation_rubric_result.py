from decimal import Decimal

from shifu.learning.core.domain.structures.code_rubric_result import (
    CodeConceptObservationResult,
    CodeCriterionResult,
)
from shifu.shared.core.domain.structures import structure


@structure
class TranslationRubricResult:
    question_key: str
    score: Decimal | None
    criterion_results: tuple[CodeCriterionResult, ...]
    concept_observations: tuple[CodeConceptObservationResult, ...]

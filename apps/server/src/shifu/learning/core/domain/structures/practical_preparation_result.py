from decimal import Decimal

from shifu.learning.core.domain.structures.practical_concept_evidence import (
    PracticalConceptEvidence,
)
from shifu.learning.core.domain.structures.practical_criterion_result import (
    PracticalCriterionResult,
)
from shifu.shared.core.domain.structures import structure


@structure
class PracticalPreparationResult:
    question_key: str
    score: Decimal | None
    closed_without_grade: bool
    criterion_results: tuple[PracticalCriterionResult, ...]
    unassessable_record_keys: tuple[str, ...]
    concept_evidence: tuple[PracticalConceptEvidence, ...]

from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class CodeCriterionResult:
    key: str
    weight_percentage: int
    level: int | str
    comment_id: str
    comment: str


@structure
class CodeConceptObservationResult:
    concept_id: str
    level: int | str
    observation_id: str


@structure
class CodeRubricResult:
    question_key: str
    score: Decimal | None
    criterion_results: tuple[CodeCriterionResult, ...]
    concept_observations: tuple[CodeConceptObservationResult, ...]

from shifu.learning.core.domain.structures.choice_evaluation_result import (
    ChoiceEvaluationResult,
)
from shifu.learning.core.domain.structures.code_evaluation_result import (
    CodeEvaluationResult,
)
from shifu.learning.core.domain.structures.qualitative_evaluation_result import (
    QualitativeEvaluationResult,
)

type EvaluationPartResult = (
    ChoiceEvaluationResult | CodeEvaluationResult | QualitativeEvaluationResult
)

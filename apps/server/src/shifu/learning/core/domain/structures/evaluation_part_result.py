from shifu.learning.core.domain.structures.choice_evaluation_result import (
    ChoiceEvaluationResult,
)
from shifu.learning.core.domain.structures.code_evaluation_result import (
    CodeEvaluationResult,
)
from shifu.learning.core.domain.structures.code_rubric_result import CodeRubricResult
from shifu.learning.core.domain.structures.fill_blanks_evaluation_result import (
    FillBlanksEvaluationResult,
)
from shifu.learning.core.domain.structures.qualitative_evaluation_result import (
    QualitativeEvaluationResult,
)
from shifu.learning.core.domain.structures.translation_rubric_result import (
    TranslationRubricResult,
)

type EvaluationPartResult = (
    ChoiceEvaluationResult
    | CodeEvaluationResult
    | CodeRubricResult
    | QualitativeEvaluationResult
    | FillBlanksEvaluationResult
    | TranslationRubricResult
)

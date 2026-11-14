from .code_rubric_evaluation_part import CodeRubricEvaluationPart
from .correctness_evaluation_part import CorrectnessEvaluationPart
from .qualitative_evaluation_part import QualitativeEvaluationPart
from .test_cases_evaluation_part import TestCasesEvaluationPart
from .translation_rubric_evaluation_part import TranslationRubricEvaluationPart

type EvaluationPart = (
    CorrectnessEvaluationPart
    | TestCasesEvaluationPart
    | QualitativeEvaluationPart
    | CodeRubricEvaluationPart
    | TranslationRubricEvaluationPart
)

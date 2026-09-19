from .correctness_evaluation_part import CorrectnessEvaluationPart
from .qualitative_evaluation_part import QualitativeEvaluationPart
from .test_cases_evaluation_part import TestCasesEvaluationPart


type EvaluationPart = (
    CorrectnessEvaluationPart | TestCasesEvaluationPart | QualitativeEvaluationPart
)

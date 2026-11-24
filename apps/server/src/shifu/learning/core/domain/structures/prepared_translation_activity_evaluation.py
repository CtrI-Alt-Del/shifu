from shifu.shared.core.domain.structures import structure

from shifu.learning.core.domain.structures.activity_rubric_assessment_decision import (
    ActivityRubricAssessmentDecision,
)
from shifu.learning.core.domain.structures.prepared_translation_question_assessment import (
    PreparedTranslationQuestionAssessment,
)


@structure
class PreparedTranslationActivityEvaluation:
    attempt_id: str
    run_id: str
    questions: tuple[PreparedTranslationQuestionAssessment, ...]
    rubric_decisions: tuple[ActivityRubricAssessmentDecision, ...] = ()

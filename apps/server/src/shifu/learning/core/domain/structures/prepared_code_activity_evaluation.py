from shifu.shared.core.domain.structures import structure

from shifu.learning.core.domain.structures.activity_rubric_assessment_decision import (
    ActivityRubricAssessmentDecision,
)
from shifu.learning.core.domain.structures.prepared_code_question_assessment import (
    PreparedCodeQuestionAssessment,
)


@structure
class PreparedCodeActivityEvaluation:
    attempt_id: str
    run_id: str
    questions: tuple[PreparedCodeQuestionAssessment, ...]
    rubric_decisions: tuple[ActivityRubricAssessmentDecision, ...] = ()

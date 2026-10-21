from shifu.shared.core.domain.structures import structure

from .prepared_code_question_assessment import PreparedCodeQuestionAssessment


@structure
class PreparedCodeActivityEvaluation:
    attempt_id: str
    run_id: str
    questions: tuple[PreparedCodeQuestionAssessment, ...]

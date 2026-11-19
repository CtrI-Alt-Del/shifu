from shifu.shared.core.domain.structures import structure

from .prepared_translation_question_assessment import (
    PreparedTranslationQuestionAssessment,
)


@structure
class PreparedTranslationActivityEvaluation:
    attempt_id: str
    run_id: str
    questions: tuple[PreparedTranslationQuestionAssessment, ...]

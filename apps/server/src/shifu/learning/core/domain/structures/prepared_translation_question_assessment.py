from shifu.shared.core.domain.structures import (
    TranslationRubricAssessmentInput,
    structure,
)


@structure
class PreparedTranslationQuestionAssessment:
    question_key: str
    assessment_input: TranslationRubricAssessmentInput

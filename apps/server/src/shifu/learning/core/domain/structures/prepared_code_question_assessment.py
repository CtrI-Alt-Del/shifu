from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    structure,
)


@structure
class PreparedCodeQuestionAssessment:
    question_key: str
    assessment_input: CodeRubricAssessmentInput

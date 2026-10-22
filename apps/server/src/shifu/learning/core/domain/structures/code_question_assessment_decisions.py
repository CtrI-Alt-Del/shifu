from shifu.shared.core.domain.structures import CodeRubricDecisions, structure


@structure
class CodeQuestionAssessmentDecisions:
    question_key: str
    decisions: CodeRubricDecisions

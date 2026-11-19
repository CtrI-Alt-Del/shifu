from shifu.shared.core.domain.structures import CodeRubricDecisions, structure


@structure
class TranslationQuestionAssessmentDecisions:
    question_key: str
    decisions: CodeRubricDecisions

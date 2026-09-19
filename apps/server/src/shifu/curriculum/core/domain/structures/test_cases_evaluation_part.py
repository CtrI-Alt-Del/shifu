from shifu.shared.core.domain.structures import structure


@structure
class TestCasesEvaluationPart:
    question_key: str
    weight_percentage: int

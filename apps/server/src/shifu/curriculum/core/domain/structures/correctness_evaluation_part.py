from shifu.shared.core.domain.structures import structure


@structure
class CorrectnessEvaluationPart:
    question_key: str
    weight_percentage: int

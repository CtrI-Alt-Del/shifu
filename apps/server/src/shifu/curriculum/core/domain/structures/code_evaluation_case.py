from shifu.shared.core.domain.structures import structure


@structure
class CodeEvaluationCase:
    name: str
    input: str
    expected_output: str
    is_initially_public: bool

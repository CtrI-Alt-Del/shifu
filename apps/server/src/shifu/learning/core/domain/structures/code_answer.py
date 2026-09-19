from shifu.shared.core.domain.structures import structure


@structure
class CodeAnswer:
    question_key: str
    source_code: str

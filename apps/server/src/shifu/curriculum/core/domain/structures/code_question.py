from shifu.shared.core.domain.structures import structure

from .code_evaluation_case import CodeEvaluationCase


@structure
class CodeQuestion:
    key: str
    prompt: str
    language: str
    evaluation_cases: tuple[CodeEvaluationCase, ...]
    starter_code: str | None = None

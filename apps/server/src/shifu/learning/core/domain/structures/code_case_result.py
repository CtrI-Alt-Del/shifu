from shifu.shared.core.domain.structures import structure


@structure
class CodeCaseResult:
    case_key: str
    passed: bool
    actual_output: str | None
    expected_output: str | None
    error: str | None

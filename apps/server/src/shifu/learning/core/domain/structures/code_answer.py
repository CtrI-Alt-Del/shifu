from shifu.shared.core.domain.structures import structure


@structure
class CodeSubmittedFile:
    path: str
    content: str


@structure
class CodeAnswer:
    question_key: str
    source_code: str | None = None
    files: tuple[CodeSubmittedFile, ...] = ()

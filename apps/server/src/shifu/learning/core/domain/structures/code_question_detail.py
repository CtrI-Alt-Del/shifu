from shifu.shared.core.domain.structures import (
    CurriculumJavascriptDependencySnapshot,
    CurriculumJavascriptInitialFileSnapshot,
    CurriculumJavascriptPermittedCommandSnapshot,
    structure,
)


@structure
class CodeQuestionCriterionDetail:
    key: str
    name: str
    weight_percentage: int


@structure
class CodeQuestionDetail:
    key: str
    kind: str
    prompt: str
    initial_files: tuple[CurriculumJavascriptInitialFileSnapshot, ...]
    entrypoint: str
    editable_paths: tuple[str, ...]
    fixed_dependencies: tuple[CurriculumJavascriptDependencySnapshot, ...]
    permitted_commands: tuple[CurriculumJavascriptPermittedCommandSnapshot, ...]
    criteria: tuple[CodeQuestionCriterionDetail, ...]

from shifu.shared.core.domain.structures import (
    CurriculumReactAdditionalFilePolicySnapshot,
    CurriculumReactDependencySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactPermittedCommandSnapshot,
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
    initial_files: tuple[
        CurriculumJavascriptInitialFileSnapshot | CurriculumReactInitialFileSnapshot,
        ...,
    ]
    entrypoint: str
    editable_paths: tuple[str, ...]
    fixed_dependencies: tuple[
        CurriculumJavascriptDependencySnapshot | CurriculumReactDependencySnapshot, ...
    ]
    permitted_commands: tuple[
        CurriculumJavascriptPermittedCommandSnapshot
        | CurriculumReactPermittedCommandSnapshot,
        ...,
    ]
    criteria: tuple[CodeQuestionCriterionDetail, ...]
    additional_file_policy: CurriculumReactAdditionalFilePolicySnapshot | None = None

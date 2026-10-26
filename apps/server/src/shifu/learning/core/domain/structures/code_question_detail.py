from shifu.shared.core.domain.structures import (
    CurriculumHtmlCssJsDependencySnapshot,
    CurriculumHtmlCssJsInitialFileSnapshot,
    CurriculumHtmlCssJsPermittedCommandSnapshot,
    CurriculumReactAdditionalFilePolicySnapshot,
    CurriculumReactDependencySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactPermittedCommandSnapshot,
    CurriculumJavascriptDependencySnapshot,
    CurriculumJavascriptInitialFileSnapshot,
    CurriculumJavascriptPermittedCommandSnapshot,
    CurriculumReactFastifyHttpExampleSnapshot,
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
        CurriculumJavascriptInitialFileSnapshot
        | CurriculumReactInitialFileSnapshot
        | CurriculumHtmlCssJsInitialFileSnapshot,
        ...,
    ]
    entrypoint: str
    editable_paths: tuple[str, ...]
    fixed_dependencies: tuple[
        CurriculumJavascriptDependencySnapshot
        | CurriculumReactDependencySnapshot
        | CurriculumHtmlCssJsDependencySnapshot,
        ...,
    ]
    permitted_commands: tuple[
        CurriculumJavascriptPermittedCommandSnapshot
        | CurriculumReactPermittedCommandSnapshot
        | CurriculumHtmlCssJsPermittedCommandSnapshot,
        ...,
    ]
    criteria: tuple[CodeQuestionCriterionDetail, ...]
    additional_file_policy: CurriculumReactAdditionalFilePolicySnapshot | None = None
    frontend_entrypoint: str | None = None
    api_entrypoint: str | None = None
    frontend_command_id: str | None = None
    api_command_id: str | None = None
    http_examples: tuple[CurriculumReactFastifyHttpExampleSnapshot, ...] = ()

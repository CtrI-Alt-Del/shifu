from pathlib import PurePosixPath
from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_code_concept_criterion_snapshot import (
    CurriculumCodeConceptCriterionSnapshot,
)


@structure
class CurriculumJavascriptInitialFileSnapshot:
    path: str
    content: str
    editable: bool

    def __post_init__(self) -> None:
        if (
            not self.path
            or self.path.startswith('/')
            or '\\' in self.path
            or '\x00' in self.path
            or any(part in ('', '.', '..') for part in self.path.split('/'))
            or (
                self.editable
                and PurePosixPath(self.path).suffix
                not in ('.js', '.mjs', '.cjs', '.txt')
            )
        ):
            raise ValidationError


@structure
class CurriculumJavascriptDependencySnapshot:
    name: str
    version: str


@structure
class CurriculumJavascriptPermittedCommandSnapshot:
    id: str
    executable: str
    arguments: tuple[str, ...]


@structure
class CurriculumJavascriptStdinQuestionSnapshot:
    key: str
    prompt: str
    initial_files: tuple[CurriculumJavascriptInitialFileSnapshot, ...]
    entrypoint: str
    fixed_dependencies: tuple[CurriculumJavascriptDependencySnapshot, ...]
    permitted_commands: tuple[CurriculumJavascriptPermittedCommandSnapshot, ...]
    concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...]
    kind: Literal['javascript_stdin'] = 'javascript_stdin'

    def __post_init__(self) -> None:
        for value in (self.key, self.prompt, self.entrypoint):
            NonEmptyText.create(value, error_type=ValidationError)
        paths = tuple(item.path for item in self.initial_files)
        if (
            self.kind != 'javascript_stdin'
            or not paths
            or len(paths) != len(set(paths))
            or self.entrypoint not in paths
            or not self.initial_files[paths.index(self.entrypoint)].editable
            or not any(item.editable for item in self.initial_files)
        ):
            raise ValidationError

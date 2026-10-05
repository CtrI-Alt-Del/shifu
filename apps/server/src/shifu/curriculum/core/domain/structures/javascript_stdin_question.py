from pathlib import PurePosixPath
from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .code_concept_criterion import CodeConceptCriterion


@structure
class JavascriptInitialFile:
    path: str
    content: str
    editable: bool

    def __post_init__(self) -> None:
        _valid_path(self.path, self.editable)


@structure
class JavascriptDependency:
    name: str
    version: str

    def __post_init__(self) -> None:
        for value in (self.name, self.version):
            NonEmptyText.create(value, error_type=InvalidActivityError)


@structure
class JavascriptPermittedCommand:
    id: str
    executable: str
    arguments: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (self.id, self.executable):
            NonEmptyText.create(value, error_type=InvalidActivityError)
        if any(not argument or '\x00' in argument for argument in self.arguments):
            raise InvalidActivityError


def _valid_path(path: str, editable: bool) -> None:
    relative = PurePosixPath(path)
    if (
        not path
        or path.startswith('/')
        or '\\' in path
        or '\x00' in path
        or any(part in ('', '.', '..') for part in path.split('/'))
        or (
            editable
            and relative.name
            in (
                'package.json',
                'package-lock.json',
                'pnpm-lock.yaml',
                'tsconfig.json',
                'vite.config.js',
            )
        )
        or (editable and relative.suffix not in ('.js', '.mjs', '.cjs', '.txt'))
    ):
        raise InvalidActivityError


@structure
class JavascriptStdinQuestion:
    key: str
    prompt: str
    initial_files: tuple[JavascriptInitialFile, ...]
    entrypoint: str
    fixed_dependencies: tuple[JavascriptDependency, ...]
    permitted_commands: tuple[JavascriptPermittedCommand, ...]
    concept_criteria: tuple[CodeConceptCriterion, ...]
    kind: Literal['javascript_stdin'] = 'javascript_stdin'

    def __post_init__(self) -> None:
        for value in (self.key, self.prompt):
            NonEmptyText.create(value, error_type=InvalidActivityError)
        paths = tuple(item.path for item in self.initial_files)
        if (
            not paths
            or len(paths) != len(set(paths))
            or self.entrypoint not in paths
            or not self.initial_files[paths.index(self.entrypoint)].editable
            or not any(item.editable for item in self.initial_files)
            or len(self.concept_criteria)
            != len({item.concept_id for item in self.concept_criteria})
            or len(self.fixed_dependencies)
            != len({item.name for item in self.fixed_dependencies})
            or len(self.permitted_commands)
            != len({item.id for item in self.permitted_commands})
            or self.kind != 'javascript_stdin'
        ):
            raise InvalidActivityError

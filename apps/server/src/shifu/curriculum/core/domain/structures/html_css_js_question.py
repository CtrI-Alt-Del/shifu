import re
from pathlib import PurePosixPath
from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .code_concept_criterion import CodeConceptCriterion

_HTML_CSS_JS_EDITABLE_SUFFIXES = frozenset({'.html', '.css', '.js'})
_SAFE_PATH_SEGMENT = re.compile(r'[A-Za-z0-9_.-]{1,64}\Z')
_FORBIDDEN_EDITABLE_NAMES = frozenset(
    {
        'package.json',
        'package-lock.json',
        'pnpm-lock.yaml',
        'yarn.lock',
        'bun.lock',
        'bun.lockb',
        'npm-shrinkwrap.json',
        'vite.config.js',
        'vite.config.ts',
        'webpack.config.js',
        'webpack.config.ts',
    }
)


@structure
class HtmlCssJsInitialFile:
    path: str
    content: str
    editable: bool

    def __post_init__(self) -> None:
        if not _is_canonical_file_path(self.path) or (
            self.editable
            and (
                _is_forbidden_editable_path(self.path)
                or PurePosixPath(self.path).suffix not in _HTML_CSS_JS_EDITABLE_SUFFIXES
            )
        ):
            raise InvalidActivityError


@structure
class HtmlCssJsDependency:
    name: str
    version: str

    def __post_init__(self) -> None:
        for value in (self.name, self.version):
            NonEmptyText.create(value, error_type=InvalidActivityError)


@structure
class HtmlCssJsPermittedCommand:
    id: str
    executable: str
    arguments: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (self.id, self.executable):
            NonEmptyText.create(value, error_type=InvalidActivityError)
        if any(not argument or '\x00' in argument for argument in self.arguments):
            raise InvalidActivityError


@structure
class HtmlCssJsQuestion:
    key: str
    prompt: str
    initial_files: tuple[HtmlCssJsInitialFile, ...]
    entrypoint: str
    fixed_dependencies: tuple[HtmlCssJsDependency, ...]
    permitted_commands: tuple[HtmlCssJsPermittedCommand, ...]
    concept_criteria: tuple[CodeConceptCriterion, ...]
    kind: Literal['html_css_js'] = 'html_css_js'

    def __post_init__(self) -> None:
        for value in (self.key, self.prompt, self.entrypoint):
            NonEmptyText.create(value, error_type=InvalidActivityError)
        paths = tuple(item.path for item in self.initial_files)
        editable_paths = tuple(
            item.path for item in self.initial_files if item.editable
        )
        if (
            not paths
            or len(paths) != len(set(paths))
            or not _paths_are_collision_free(paths)
            or self.entrypoint not in editable_paths
            or PurePosixPath(self.entrypoint).suffix != '.html'
            or not editable_paths
            or len(self.concept_criteria)
            != len({item.concept_id for item in self.concept_criteria})
            or len(self.fixed_dependencies)
            != len({item.name for item in self.fixed_dependencies})
            or len(self.permitted_commands)
            != len({item.id for item in self.permitted_commands})
            or self.kind != 'html_css_js'
        ):
            raise InvalidActivityError


def _is_canonical_file_path(path: str) -> bool:
    return bool(
        path
        and len(path) <= 240
        and not path.startswith('/')
        and '\\' not in path
        and '\x00' not in path
        and all(
            part not in ('', '.', '..')
            and not part.startswith('.')
            and _SAFE_PATH_SEGMENT.fullmatch(part)
            for part in path.split('/')
        )
        and PurePosixPath(path).name
    )


def _is_forbidden_editable_path(path: str) -> bool:
    name = PurePosixPath(path).name.casefold()
    return (
        name in _FORBIDDEN_EDITABLE_NAMES
        or (name.startswith('tsconfig.') and name.endswith('.json'))
        or '.config.' in name
        or any(part.casefold() in {'.git', 'node_modules'} for part in path.split('/'))
    )


def _paths_are_collision_free(paths: tuple[str, ...]) -> bool:
    path_set = set(paths)
    return all(
        '/'.join(PurePosixPath(path).parts[:index]) not in path_set
        for path in paths
        for index in range(1, len(PurePosixPath(path).parts))
    )

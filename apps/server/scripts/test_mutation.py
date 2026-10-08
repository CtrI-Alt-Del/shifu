"""Run mutation tests in an isolated copy with explicit, change-scoped targets."""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

SERVER = Path(__file__).resolve().parents[1]


def git_paths(root: Path, base: str | None) -> set[Path]:
    def git(*arguments: str) -> list[str]:
        result = subprocess.run(  # noqa: S603 - argv is literal Git commands; base is verified.
            [shutil.which('git') or '/usr/bin/git', '-C', str(root), *arguments],
            check=True,
            capture_output=True,
        )
        return os.fsdecode(result.stdout).rstrip('\0').split('\0')

    repository = Path(git('rev-parse', '--show-toplevel')[0].strip())

    names = set(git('diff', '--name-only', '-z', '--diff-filter=ACMR', 'HEAD', '--'))
    names.update(git('ls-files', '--others', '--exclude-standard', '-z'))
    if base is None and git('branch', '--show-current')[0].strip() != 'main':
        for candidate in ('origin/main', 'main'):
            try:
                git(
                    'rev-parse',
                    '--verify',
                    '--end-of-options',
                    f'{candidate}^{{commit}}',
                )
            except subprocess.CalledProcessError:
                continue
            base = candidate
            break
        else:
            raise ValueError(
                'No main ref available; pass --base REF or exact --files paths.'
            )
    if base:
        commit = git('rev-parse', '--verify', '--end-of-options', f'{base}^{{commit}}')[
            0
        ].strip()
        names.update(
            git(
                'diff',
                '--name-only',
                '-z',
                '--diff-filter=ACMR',
                f'{commit}...HEAD',
                '--',
            )
        )
    return {repository / name for name in names if name}


def eligible(path: Path, root: Path, core: bool = False) -> bool:
    relative = path.relative_to(root)
    if path.is_symlink() or any(character in str(relative) for character in '*?[]'):
        raise ValueError(f'Mutation source requires a regular exact path: {relative}')

    return (
        relative.parts[0] == 'src'
        and path.suffix == '.py'
        and path.name != '__init__.py'
        and not {'fakers', 'generated', '__pycache__'}.intersection(relative.parts)
        and (
            not core
            or (
                len(relative.parts) >= 6
                and relative.parts[:2] == ('src', 'shifu')
                and relative.parts[3] == 'core'
                and relative.parts[4] == 'use_cases'
            )
        )
    )


def import_graph(root: Path) -> dict[Path, set[Path]]:
    """Follow static imports including package barrels and relative imports."""
    modules: dict[str, Path] = {}
    for folder in ('src', 'tests'):
        for path in (root / folder).rglob('*.py'):
            relative = path.relative_to(root / 'src' if folder == 'src' else root)
            parts = list(relative.with_suffix('').parts)
            if parts[-1] == '__init__':
                parts.pop()
            modules['.'.join(parts)] = path

    graph: dict[Path, set[Path]] = {}
    for module, path in modules.items():
        imports: set[Path] = set()
        package = (
            module.split('.') if path.name == '__init__.py' else module.split('.')[:-1]
        )

        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                prefix = (
                    '.'.join(package[: len(package) - node.level + 1])
                    if node.level
                    else ''
                )
                name = '.'.join(part for part in (prefix, node.module) if part)
                names.append(name)
                names.extend(f'{name}.{alias.name}' for alias in node.names)
            for name in names:
                if name in modules:
                    imports.add(modules[name])
        graph[path] = imports
    return graph


def dependencies(path: Path, graph: dict[Path, set[Path]]) -> set[Path]:
    found: set[Path] = set()
    pending = [path]
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        pending.extend(graph.get(current, ()))
    return found


def is_core_use_case_test(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    return (
        len(parts) >= 4
        and parts[0] == 'tests'
        and (
            any(
                parts[index : index + 2] == ('core', 'use_cases')
                for index in range(1, len(parts) - 1)
            )
            or (len(parts) >= 5 and parts[1] == 'core' and parts[3] == 'use_cases')
        )
    )


def select(
    root: Path, changed: set[Path], full: bool, core: bool = False
) -> tuple[list[Path], list[Path]]:
    graph = import_graph(root)
    production = {path for path in graph if eligible(path, root, core)}
    tests = {
        path
        for path in graph
        if path.name.startswith('test_')
        and path.is_relative_to(root / 'tests')
        and (not core or is_core_use_case_test(path, root))
    }

    if full:
        return sorted(production), sorted(tests)
    targets = production & changed
    changed_tests = tests & changed
    for test in changed_tests:
        targets.update(production & dependencies(test, graph))
    selected_tests = {test for test in tests if dependencies(test, graph) & targets}
    return sorted(targets), sorted(selected_tests | changed_tests)


def parse_shard(value: str) -> tuple[int, int]:
    try:
        index, total = (int(part) for part in value.split('/'))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            'Expected --shard N/TOTAL, for example 1/4.'
        ) from error
    if not 1 <= index <= total:
        raise argparse.ArgumentTypeError('Shard requires 1 <= N <= TOTAL.')
    return index, total


def shard_targets(
    root: Path, targets: list[Path], shard: tuple[int, int]
) -> list[Path]:
    """Greedily balance AST weight with stable path and shard-index tie breaks."""
    index, total = shard
    weighted = [
        (sum(1 for _ in ast.walk(ast.parse(path.read_text()))), path)
        for path in set(targets)
    ]
    weighted.sort(key=lambda item: (-item[0], item[1].relative_to(root).as_posix()))
    assignments: list[list[Path]] = [[] for _ in range(total)]
    weights = [0] * total
    for weight, path in weighted:
        destination = min(range(total), key=lambda number: (weights[number], number))
        assignments[destination].append(path)
        weights[destination] += weight
    return sorted(assignments[index - 1])


def report_directory(root: Path, shard: tuple[int, int] | None = None) -> Path:
    report = root / 'test-results' / 'mutation'
    if shard is not None:
        index, total = shard
        report /= f'shard-{index}-of-{total}'
    return report


def checked_paths(values: list[str], root: Path, folder: str) -> set[Path]:
    paths: set[Path] = set()
    for value in values:
        path = (root / value).resolve()
        if (
            not path.is_relative_to(root / folder)
            or not path.is_file()
            or path.suffix != '.py'
        ):
            raise ValueError(f'Expected an existing {folder}/ Python file: {value}')
        if folder == 'tests' and not path.name.startswith('test_'):
            raise ValueError(f'Expected a test_*.py file: {value}')
        if any(character in value for character in '*?[]'):
            raise ValueError(f'Use exact paths, not globs: {value}')
        paths.add(path)
    return paths


@contextmanager
def mutation_runtime(core: bool, env: dict[str, str]) -> Iterator[None]:
    if core:
        env.pop('SHIFU_RUN_REAL_INNGEST_TESTS', None)
        env.pop('PYTEST_PLUGINS', None)
        yield
        return

    from testcontainers.community.redis import RedisContainer

    env['SHIFU_RUN_REAL_INNGEST_TESTS'] = '1'
    # Protect shared developer Redis from application fixture cleanup.
    with RedisContainer('redis:7-alpine') as redis:
        env['REDIS_URL'] = (
            f'redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0'
        )
        yield


def selection_by_module(
    root: Path, targets: list[Path], tests: list[Path]
) -> dict[str, dict[str, list[str]]]:
    modules: dict[str, dict[str, list[str]]] = {}
    for category, paths in (('mutate', targets), ('tests', tests)):
        for path in sorted(paths):
            relative = path.relative_to(root)
            parts = relative.parts
            module = 'unattributed'
            if len(parts) >= 4 and parts[:2] == ('src', 'shifu'):
                module = parts[2]
            elif len(parts) >= 5 and parts[0] == 'tests':
                module = parts[2] if parts[1] == 'core' else parts[1]
            modules.setdefault(module, {'mutate': [], 'tests': []})[category].append(
                str(relative)
            )
    return dict(sorted(modules.items()))


def module_outcomes(results: str) -> dict[str, dict[str, int]]:
    """Count complete mutmut results, retaining unknown identifier namespaces."""
    modules: dict[str, dict[str, int]] = {}
    for line in results.splitlines():
        identifier, separator, status = line.strip().rpartition(': ')
        if not separator or '__mutmut_' not in identifier:
            continue
        parts = identifier.split('.')
        module = parts[1] if len(parts) >= 3 and parts[0] == 'shifu' else 'unattributed'
        counts = modules.setdefault(module, {'total': 0})
        counts['total'] += 1
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(modules.items()))


def run(
    root: Path,
    targets: list[Path],
    tests: list[Path],
    core: bool = False,
    shard: tuple[int, int] | None = None,
) -> int:
    report = report_directory(root, shard)
    report.mkdir(parents=True, exist_ok=True)
    selection = {
        'mutate': [str(path.relative_to(root)) for path in targets],
        'tests': [str(path.relative_to(root)) for path in tests],
        'modules': selection_by_module(root, targets, tests),
    }
    (report / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    print(json.dumps(selection, indent=2), flush=True)

    with tempfile.TemporaryDirectory(prefix='shifu-mutation-') as directory:
        workspace = Path(directory)
        for folder in ('src', 'tests', 'migrations', 'scripts'):
            if (root / folder).exists():
                shutil.copytree(
                    root / folder,
                    workspace / folder,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
                )

        shutil.copy2(root / 'alembic.ini', workspace / 'alembic.ini')
        if core:
            # Application conftest registers autouse Redis/PostgreSQL/job fixtures.
            # Core tests own their mocks and module-local fixtures instead.
            (workspace / 'tests' / 'conftest.py').unlink(missing_ok=True)
        configuration = (root / 'pyproject.toml').read_text()
        configuration += '\n[tool.mutmut]\nsource_paths = ["src"]\n'
        configuration += f'only_mutate = {json.dumps(selection["mutate"])}\n'
        configuration += (
            f'pytest_add_cli_args_test_selection = {json.dumps(selection["tests"])}\n'
        )
        configuration += 'also_copy = ["migrations", "alembic.ini", "scripts"]\n'
        (workspace / 'pyproject.toml').write_text(configuration)

        env = dict(os.environ)
        with mutation_runtime(core, env):
            result = subprocess.run(
                [sys.executable, '-m', 'mutmut', 'run', '--max-children', '1'],
                cwd=workspace,
                env=env,
            )

        report_exit_codes: dict[str, int] = {}
        for command, name in (
            (['results', '--all', 'true'], 'results.txt'),
            (['export-cicd-stats'], 'stats.txt'),
        ):
            output = subprocess.run(  # noqa: S603 - command comes from a literal tuple.
                [sys.executable, '-m', 'mutmut', *command],
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
            )
            report_exit_codes[name] = output.returncode
            (report / name).write_text(output.stdout + output.stderr)
        outcomes = module_outcomes((report / 'results.txt').read_text())
        (report / 'module-results.json').write_text(
            json.dumps(
                {
                    'modules': outcomes,
                    'source': 'mutmut results --all true',
                    'status': 'complete'
                    if report_exit_codes['results.txt'] == 0
                    else 'failed',
                    'results_exit_code': report_exit_codes['results.txt'],
                },
                indent=2,
            )
            + '\n'
        )
        mutants = workspace / 'mutants'
        for name in ('mutmut-cicd-stats.json', 'mutmut-stats.json'):
            if (mutants / name).exists():
                shutil.copy2(mutants / name, report / name)
            if mutants.exists():
                for path in mutants.rglob('*.meta'):
                    destination = report / 'metadata' / path.relative_to(mutants)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)

        return result.returncode or next(
            (code for code in report_exit_codes.values() if code), 0
        )


def validate_shard_scope(
    parser: argparse.ArgumentParser, arguments: argparse.Namespace
) -> None:
    if arguments.shard and (not arguments.all or not arguments.core or arguments.tests):
        parser.error(
            '--shard requires --all --core and cannot narrow tests with --tests.'
        )


def apply_shard(
    root: Path, targets: list[Path], shard: tuple[int, int] | None
) -> list[Path]:
    return targets if shard is None else shard_targets(root, targets, shard)


def record_empty_shard(root: Path, shard: tuple[int, int] | None) -> None:
    if shard is None:
        return
    report = report_directory(root, shard)
    report.mkdir(parents=True, exist_ok=True)
    (report / 'selection.json').write_text(
        json.dumps({'mutate': [], 'tests': [], 'status': 'not-applicable'}, indent=2)
        + '\n'
    )
    print('Empty mutation shard: not applicable.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        '--all', action='store_true', help='Mutate all eligible production source (CI).'
    )
    scope.add_argument(
        '--base', help='Include branch changes since the merge base of this Git ref.'
    )
    scope.add_argument(
        '--files', nargs='+', help='Exact src/ files; overrides Git selection.'
    )
    parser.add_argument(
        '--core',
        action='store_true',
        help='Restrict mutation targets to src/shifu/<module>/core/use_cases/ (including shared).',
    )
    parser.add_argument(
        '--tests',
        nargs='+',
        help='Exact related tests/ files; overrides static import selection.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print target/test selections without running mutmut.',
    )
    parser.add_argument(
        '--shard', type=parse_shard, help='CI shard N/TOTAL; requires --all --core.'
    )
    arguments = parser.parse_args()
    validate_shard_scope(parser, arguments)

    try:
        changed: set[Path] = (
            set()
            if arguments.all
            else (
                checked_paths(arguments.files, SERVER, 'src')
                if arguments.files
                else git_paths(SERVER, arguments.base)
            )
        )
        if (
            not arguments.files
            and not arguments.all
            and any(
                path.is_relative_to(SERVER)
                and (
                    path.name in {'conftest.py', 'pyproject.toml', 'uv.lock'}
                    or path.is_relative_to(SERVER / 'tests' / 'fixtures')
                )
                for path in changed
            )
        ):
            parser.error(
                'Fixture/configuration changes require explicit --files and related --tests, or --all in CI.'
            )

        targets, tests = select(SERVER, changed, arguments.all, arguments.core)
        if arguments.files and len(targets) != len(changed):
            parser.error(
                'Explicit source selection contains excluded/non-runtime files'
                + (
                    ' or files outside src/shifu/<module>/core/use_cases/.'
                    if arguments.core
                    else '.'
                )
            )
        if arguments.tests:
            if arguments.all:
                parser.error('--all cannot narrow the test suite with --tests.')
            tests = sorted(checked_paths(arguments.tests, SERVER, 'tests'))
            if arguments.core and any(
                not is_core_use_case_test(path, SERVER) for path in tests
            ):
                parser.error('--core requires core use-case test paths in --tests.')
        targets = apply_shard(SERVER, targets, arguments.shard)
        if not targets:
            record_empty_shard(SERVER, arguments.shard)
            print(
                'No changed eligible Python mutation targets. No mutation tests executed.'
            )
            return 0
        if not tests:
            parser.error(
                'Mutation targets have no related tests; specify exact --tests paths.'
            )

        if arguments.dry_run:
            print(
                json.dumps(
                    {
                        'mutate': [str(path.relative_to(SERVER)) for path in targets],
                        'tests': [str(path.relative_to(SERVER)) for path in tests],
                    },
                    indent=2,
                )
            )
            return 0
        return run(SERVER, targets, tests, core=arguments.core, shard=arguments.shard)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())

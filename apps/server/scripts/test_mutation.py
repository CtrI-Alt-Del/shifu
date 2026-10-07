"""Run mutation tests in an isolated copy with explicit, change-scoped targets."""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

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


def eligible(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if path.is_symlink() or any(character in str(relative) for character in '*?[]'):
        raise ValueError(f'Mutation source requires a regular exact path: {relative}')

    return (
        relative.parts[0] == 'src'
        and path.suffix == '.py'
        and path.name != '__init__.py'
        and not {'fakers', 'generated', '__pycache__'}.intersection(relative.parts)
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


def select(root: Path, changed: set[Path], full: bool) -> tuple[list[Path], list[Path]]:
    graph = import_graph(root)
    production = {path for path in graph if eligible(path, root)}
    tests = {
        path
        for path in graph
        if path.name.startswith('test_') and path.is_relative_to(root / 'tests')
    }

    if full:
        return sorted(production), sorted(tests)
    targets = production & changed
    changed_tests = tests & changed
    for test in changed_tests:
        targets.update(production & dependencies(test, graph))
    selected_tests = {test for test in tests if dependencies(test, graph) & targets}
    return sorted(targets), sorted(selected_tests | changed_tests)


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


def run(root: Path, targets: list[Path], tests: list[Path]) -> int:
    from testcontainers.community.redis import RedisContainer

    report = root / 'test-results' / 'mutation'
    report.mkdir(parents=True, exist_ok=True)
    selection = {
        'mutate': [str(path.relative_to(root)) for path in targets],
        'tests': [str(path.relative_to(root)) for path in tests],
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
        configuration = (root / 'pyproject.toml').read_text()
        configuration += '\n[tool.mutmut]\nsource_paths = ["src"]\n'
        configuration += f'only_mutate = {json.dumps(selection["mutate"])}\n'
        configuration += (
            f'pytest_add_cli_args_test_selection = {json.dumps(selection["tests"])}\n'
        )
        configuration += 'also_copy = ["migrations", "alembic.ini", "scripts"]\n'
        (workspace / 'pyproject.toml').write_text(configuration)

        env = {**os.environ, 'SHIFU_RUN_REAL_INNGEST_TESTS': '1'}
        # Root conftest clears rate-limit keys before the ordinary Redis fixture:
        # protect any developer Redis by supplying another disposable instance.
        with RedisContainer('redis:7-alpine') as redis:
            env['REDIS_URL'] = (
                f'redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0'
            )
            result = subprocess.run(
                [sys.executable, '-m', 'mutmut', 'run', '--max-children', '1'],
                cwd=workspace,
                env=env,
            )

        for command, name in (
            ('results', 'results.txt'),
            ('export-cicd-stats', 'stats.txt'),
        ):
            output = subprocess.run(  # noqa: S603 - command comes from a literal tuple.
                [sys.executable, '-m', 'mutmut', command],
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
            )
            (report / name).write_text(output.stdout + output.stderr)
        mutants = workspace / 'mutants'
        for name in ('mutmut-cicd-stats.json', 'mutmut-stats.json'):
            if (mutants / name).exists():
                shutil.copy2(mutants / name, report / name)
            if mutants.exists():
                for path in mutants.rglob('*.meta'):
                    destination = report / 'metadata' / path.relative_to(mutants)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)

        return result.returncode


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
        '--tests',
        nargs='+',
        help='Exact related tests/ files; overrides static import selection.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print target/test selections without running mutmut.',
    )
    arguments = parser.parse_args()

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

        targets, tests = select(SERVER, changed, arguments.all)
        if arguments.files and len(targets) != len(changed):
            parser.error(
                'Explicit source selection contains excluded/non-runtime files.'
            )
        if arguments.tests:
            if arguments.all:
                parser.error('--all cannot narrow the test suite with --tests.')
            tests = sorted(checked_paths(arguments.tests, SERVER, 'tests'))
        if not targets:
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
        return run(SERVER, targets, tests)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())

"""Check coverage of executable Python code changed since a Git commit."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING, cast

from coverage import Coverage

if TYPE_CHECKING:
    from collections.abc import Sequence


SERVER = Path(__file__).resolve().parents[1]
_HUNK = re.compile(rb'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
_FLOORS = {'statements': 85, 'functions': 85, 'lines': 85, 'branches': 80}


@dataclass(frozen=True)
class Metric:
    covered: int = 0
    total: int = 0

    @property
    def percentage(self) -> float:
        return 100 * self.covered / self.total if self.total else 100.0


def _git(root: Path, *arguments: str) -> bytes:
    git = shutil.which('git')
    if git is None:
        raise ValueError('Git is required for changed-code coverage.')
    return subprocess.run(  # noqa: S603 - fixed executable and argv, no shell.
        [git, '-C', str(root), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def changed_lines(root: Path, base: str) -> dict[Path, set[int]]:
    """Include committed, staged, unstaged and untracked source changes."""
    commit = os.fsdecode(
        _git(root, 'rev-parse', '--verify', '--end-of-options', f'{base}^{{commit}}')
    ).strip()
    names = _git(
        root,
        'diff',
        '--relative',
        '--name-only',
        '-z',
        '--diff-filter=ACMR',
        commit,
        '--',
        'src/shifu',
    ).split(b'\0')
    untracked = set(
        _git(
            root, 'ls-files', '--others', '--exclude-standard', '-z', '--', 'src/shifu'
        )
        .rstrip(b'\0')
        .split(b'\0')
    )
    names.extend(untracked)
    result: dict[Path, set[int]] = {}
    for name in names:
        relative = os.fsdecode(name)
        if not relative.startswith('src/shifu/') or not relative.endswith('.py'):
            continue
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        patch = (
            b''
            if name in untracked
            else _git(
                root, 'diff', '--unified=0', '--no-ext-diff', commit, '--', relative
            )
        )
        lines: set[int] = set()
        for line in patch.splitlines():
            match = _HUNK.match(line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2) or b'1')
                lines.update(range(start, start + count))
        if not patch:
            lines.update(range(1, len(path.read_bytes().splitlines()) + 1))
        if lines:
            result[path] = lines
    return result


def _functions(source: str, changed: set[int], statements: set[int]) -> list[int]:
    tree = ast.parse(source)
    entries: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        end = node.end_lineno or node.lineno
        if not any(node.lineno <= line <= end for line in changed):
            continue
        body_lines = {
            line
            for child in node.body
            for line in range(child.lineno, (child.end_lineno or child.lineno) + 1)
        }
        executable = sorted((body_lines & statements) - {node.lineno})
        if executable:
            entries.append(executable[0])
    return entries


def measure(
    changed: dict[Path, set[int]], coverage_file: Path
) -> dict[Path, dict[str, Metric]]:
    if not coverage_file.is_file():
        raise ValueError(f'Coverage data file does not exist: {coverage_file}')
    cov = Coverage(data_file=str(coverage_file))
    cov.load()
    if not cov.get_data().has_arcs():
        raise ValueError('Coverage data must be collected with --branch.')

    results: dict[Path, dict[str, Metric]] = {}
    for path, lines in sorted(changed.items()):
        counts = {name: [0, 0] for name in _FLOORS}
        _, executable, _, missing, _ = cov.analysis2(str(path))
        statements = set(executable) & lines
        covered = statements - set(missing)
        counts['statements'][0] += len(covered)
        counts['statements'][1] += len(statements)
        counts['lines'][0] += len(covered)
        counts['lines'][1] += len(statements)

        entries = _functions(path.read_text(), statements, set(executable))
        counts['functions'][0] += sum(entry not in missing for entry in entries)
        counts['functions'][1] += len(entries)

        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / 'coverage.json'
            cov.json_report(morfs=[str(path)], outfile=str(report_path))
            report: dict[str, object] = json.loads(report_path.read_text())
        files = cast('dict[str, dict[str, object]]', report['files'])
        file_report = next(iter(files.values()))
        for field, covered_branch in (
            ('executed_branches', True),
            ('missing_branches', False),
        ):
            arcs = cast('list[list[int]]', file_report[field])
            for origin, destination in arcs:
                if origin in lines or destination in lines:
                    counts['branches'][1] += 1
                    counts['branches'][0] += covered_branch
        results[path] = {name: Metric(*pair) for name, pair in counts.items()}
    return results


def run_tests(root: Path, tests: Sequence[str], coverage_file: Path) -> None:
    selected: list[str] = []
    for value in tests:
        path = (root / value).resolve()
        if (
            not path.is_relative_to(root / 'tests')
            or not path.is_file()
            or not path.name.startswith('test_')
            or path.suffix != '.py'
        ):
            raise ValueError(f'Expected an existing tests/**/test_*.py path: {value}')
        selected.append(str(path.relative_to(root)))
    if not selected:
        raise ValueError('Specify at least one --tests path for a local coverage run.')

    with tempfile.TemporaryDirectory(dir=coverage_file.parent) as directory:
        run_file = Path(directory) / coverage_file.name
        command = [
            sys.executable,
            '-m',
            'coverage',
            'run',
            '--branch',
            '--parallel-mode',
            '--source=src/shifu',
            f'--data-file={run_file}',
            '-m',
            'pytest',
            *selected,
        ]
        subprocess.run(command, cwd=root, check=True)  # noqa: S603 - explicit argv.
        cov = Coverage(data_file=str(coverage_file))
        cov.erase()
        cov.combine(data_paths=[directory], strict=True)
        cov.save()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, help='Git commit to compare with.')
    parser.add_argument(
        '--coverage-file',
        type=Path,
        default=SERVER / 'test-results/changed-coverage/.coverage',
        help='Existing combined coverage.py data, or output for --tests.',
    )
    parser.add_argument(
        '--tests',
        action='append',
        default=[],
        metavar='PATH',
        help='Run one explicit test file under coverage; repeat for more files.',
    )
    args = parser.parse_args(argv)
    try:
        changed = changed_lines(SERVER, args.base)
        if not changed:
            print('No changed Server production Python files.')
            return 0
        if args.tests:
            args.coverage_file.parent.mkdir(parents=True, exist_ok=True)
            run_tests(SERVER, args.tests, args.coverage_file)
        metrics = measure(changed, args.coverage_file)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))

    failed = False
    for path, file_metrics in metrics.items():
        print(path.relative_to(SERVER))
        for name, floor in _FLOORS.items():
            metric = file_metrics[name]
            print(
                f'  {name}: {metric.covered}/{metric.total} '
                f'({metric.percentage:.1f}%; minimum {floor}%)'
            )
            failed |= metric.percentage < floor
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())

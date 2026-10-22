"""Gate changed Server source files using Coverage.py's machine-readable report."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

STATEMENT_THRESHOLD = 85.0
LINE_THRESHOLD = 85.0
FUNCTION_THRESHOLD = 85.0
BRANCH_THRESHOLD = 80.0


@dataclass(frozen=True)
class FunctionEntry:
    name: str
    code_start_line: int
    first_body_line: int
    first_body_end_line: int


@dataclass(frozen=True)
class Metric:
    covered: int
    total: int

    @property
    def percent(self) -> float:
        return 100.0 if self.total == 0 else 100.0 * self.covered / self.total


@dataclass(frozen=True)
class LineRange:
    start: int
    end: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Enforce changed-file coverage from a branch-enabled Coverage.py run. '
            'Run from apps/server.'
        ),
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        '--base',
        help='Git ref to compare with HEAD, for example origin/main',
    )
    selection.add_argument(
        '--file',
        dest='files',
        action='append',
        default=[],
        help='Changed path to check; may be repeated',
    )
    selection.add_argument(
        '--files',
        dest='file_groups',
        nargs='+',
        action='append',
        help='Changed paths to check',
    )
    parser.add_argument('--report', type=Path, default=Path('coverage.json'))
    parser.add_argument('--data-file', type=Path, default=Path('.coverage'))
    args = parser.parse_args()
    if args.file_groups:
        args.files = [path for group in args.file_groups for path in group]
    else:
        args.files = args.files or []
    return args


def changed_paths(base: str) -> list[Path]:
    try:
        command = [
            'git',
            'diff',
            '--name-only',
            '--diff-filter=ACMR',
            f'{base}...HEAD',
        ]
        result = subprocess.run(  # noqa: S603 - argv is fixed and base is a revision label.
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            f'Could not discover changed files from {base!r}: {error}'
        ) from error
    return [Path(line) for line in result.stdout.splitlines() if line]


def changed_line_ranges(base: str, path: Path, root: Path) -> list[LineRange]:
    repository_root = root.parent.parent
    repository_path = Path('apps') / 'server' / path.relative_to(root)
    try:
        command = [
            'git',
            'diff',
            '--unified=0',
            '--no-color',
            '--diff-filter=ACMR',
            f'{base}...HEAD',
            '--',
            repository_path.as_posix(),
        ]
        result = subprocess.run(  # noqa: S603 - argv is fixed and base is a revision label.
            command,
            check=True,
            capture_output=True,
            text=True,
            cwd=repository_root,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            f'Could not discover changed lines for {repository_path} from {base!r}: {error}'
        ) from error

    ranges: list[LineRange] = []
    for line in result.stdout.splitlines():
        if not line.startswith('@@'):
            continue
        try:
            header = line.split('@@', 2)[1]
            new_range = header.split('+', 1)[1].split(' ', 1)[0]
            start_text, _, count_text = new_range.partition(',')
            start = int(start_text)
            count = int(count_text) if count_text else 1
        except (IndexError, ValueError) as error:
            raise RuntimeError(
                f'Could not parse changed line range {line!r} for {repository_path}'
            ) from error
        if count > 0:
            ranges.append(LineRange(start=start, end=start + count - 1))
    return ranges


def normalize_source_path(path: Path, root: Path) -> Path | None:
    # `git diff` reports paths from the repository root even when this checker
    # runs from apps/server. Accept that form alongside paths relative to the
    # current working directory (used by --file/--files).
    if (
        not path.is_absolute()
        and root.name == 'server'
        and root.parent.name == 'apps'
        and path.parts[:2] == ('apps', 'server')
    ):
        path = Path(*path.parts[2:])
    candidate = path if path.is_absolute() else root / path
    candidate = candidate.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None
    if relative.parts[:2] != ('src', 'shifu') or candidate.suffix != '.py':
        return None
    return candidate


def first_executable_statement(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.stmt | None:
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body.pop(0)
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return None
    if (
        len(body) == 1
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is Ellipsis
    ):
        return None
    return body[0] if body else None


def has_abstractmethod_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        name = decorator.id if isinstance(decorator, ast.Name) else None
        if isinstance(decorator, ast.Attribute):
            name = decorator.attr
        if name in {'abstractmethod', 'overload'}:
            return True
    return False


def function_entries(path: Path) -> list[FunctionEntry]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    entries: list[FunctionEntry] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if has_abstractmethod_decorator(node):
            continue
        first_statement = first_executable_statement(node)
        if first_statement is None:
            continue
        decorator_lines = [decorator.lineno for decorator in node.decorator_list]
        first_statement_lines = [first_statement.lineno]
        if isinstance(first_statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            first_statement_lines.extend(
                decorator.lineno for decorator in first_statement.decorator_list
            )
        code_start = min([node.lineno, *decorator_lines])
        entries.append(
            FunctionEntry(
                name=node.name,
                code_start_line=code_start,
                first_body_line=min(first_statement_lines),
                first_body_end_line=max(
                    first_statement.end_lineno or first_statement.lineno,
                    *first_statement_lines,
                ),
            ),
        )
    return entries


def has_function_entry_arc(entry: FunctionEntry, arcs: set[tuple[int, int]]) -> bool:
    return any(
        (-entry.code_start_line, line) in arcs
        for line in range(entry.first_body_line, entry.first_body_end_line + 1)
    )


def load_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f'Could not read coverage JSON report {path}: {error}'
        ) from error
    if not report.get('meta', {}).get('branch_coverage'):
        raise RuntimeError('Coverage JSON must be generated from a branch-enabled run')
    files = report.get('files')
    if not isinstance(files, dict):
        raise TypeError("Coverage JSON has no per-file 'files' object")
    return cast('dict[str, Any]', files)


def normalized_report_files(
    files: dict[str, Any], root: Path
) -> dict[Path, dict[str, Any]]:
    normalized: dict[Path, dict[str, Any]] = {}
    for name, details in files.items():
        path = Path(name)
        candidate = path if path.is_absolute() else root / path
        normalized[candidate.resolve()] = details
    return normalized


def load_arcs(data_file: Path) -> dict[Path, set[tuple[int, int]]]:
    try:
        from coverage import CoverageData

        data = CoverageData(basename=str(data_file))
        data.read()
    except Exception as error:  # Coverage.py reports several file/read error types.
        raise RuntimeError(
            f'Could not read Coverage.py arc data {data_file}: {error}'
        ) from error
    if not data.has_arcs():
        raise RuntimeError('Coverage.py data has no arcs; rerun with --branch')
    result: dict[Path, set[tuple[int, int]]] = {}
    for filename in data.measured_files():
        arcs = data.arcs(filename)
        result[Path(filename).resolve()] = set(arcs or [])
    return result


def metric(covered: int, total: int) -> Metric:
    return Metric(covered=covered, total=total)


def render_metric(name: str, value: Metric) -> str:
    return f'{name} {value.percent:5.1f}% ({value.covered}/{value.total})'


def overlaps(location: object, ranges: list[LineRange]) -> bool:
    if not isinstance(location, dict):
        return False
    start = location.get('start')
    end = location.get('end')
    if not isinstance(start, dict) or not isinstance(end, dict):
        return False
    start_line = start.get('line')
    end_line = end.get('line')
    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return False
    return any(
        start_line <= changed.end and end_line >= changed.start
        for changed in ranges
    )


def metric_for_changed_lines(
    details: dict[str, Any],
    name: str,
    ranges: list[LineRange],
) -> Metric:
    executed_lines = details.get('executed_lines')
    missing_lines = details.get('missing_lines')
    if not isinstance(executed_lines, list) or not isinstance(missing_lines, list):
        raise RuntimeError('line coverage data is missing')

    def is_changed(line: int) -> bool:
        return any(changed.start <= line <= changed.end for changed in ranges)

    if name in {'lines', 'statements'}:
        measured_lines = {
            line for line in [*executed_lines, *missing_lines] if isinstance(line, int)
        }
        changed_lines = [line for line in measured_lines if is_changed(line)]
        return metric(
            sum(line in executed_lines for line in changed_lines),
            len(changed_lines),
        )

    if name == 'functions':
        functions = details.get('functions')
        if not isinstance(functions, dict):
            raise RuntimeError('function coverage data is missing')
        changed_functions: list[bool] = []
        for function in functions.values():
            if not isinstance(function, dict):
                continue
            start_line = function.get('start_line')
            summary = function.get('summary')
            function_executed = function.get('executed_lines')
            if (
                isinstance(start_line, int)
                and is_changed(start_line)
                and isinstance(summary, dict)
                and int(summary.get('num_statements', 0)) > 0
                and isinstance(function_executed, list)
            ):
                changed_functions.append(bool(function_executed))
        return metric(sum(changed_functions), len(changed_functions))

    executed_branches = details.get('executed_branches')
    missing_branches = details.get('missing_branches')
    if not isinstance(executed_branches, list) or not isinstance(
        missing_branches, list
    ):
        raise RuntimeError('branch coverage data is missing')

    def branch_is_changed(branch: object) -> bool:
        return (
            isinstance(branch, list)
            and bool(branch)
            and isinstance(branch[0], int)
            and branch[0] > 0
            and is_changed(branch[0])
        )

    executed = [branch for branch in executed_branches if branch_is_changed(branch)]
    missing = [branch for branch in missing_branches if branch_is_changed(branch)]
    return metric(len(executed), len(executed) + len(missing))


def main() -> int:
    args = parse_args()
    root = Path.cwd().resolve()
    raw_paths = (
        changed_paths(args.base) if args.base else [Path(item) for item in args.files]
    )
    eligible = sorted(
        {
            normalized
            for path in raw_paths
            if (normalized := normalize_source_path(path, root))
        },
    )
    if not eligible:
        message = 'No changed eligible Server production files.'
        if args.base:
            print(f'Coverage gate cannot run: {message}', file=sys.stderr)
            return 2
        print(message)
        return 0

    try:
        report_files = normalized_report_files(load_report(args.report), root)
    except (RuntimeError, TypeError) as error:
        print(f'Coverage gate cannot run: {error}', file=sys.stderr)
        return 2

    failed = False
    print(
        'Coverage denominators include only executable statements, functions, lines, and '
        'branches overlapping source lines changed in the current diff; branches use '
        'Coverage.py possible/executed arcs.'
    )
    for path in eligible:
        display_path = path.relative_to(root)
        details = report_files.get(path)
        if details is None:
            failed = True
            print(f'FAIL {display_path}: missing from JSON report')
            continue

        try:
            ranges = (
                changed_line_ranges(args.base, path, root)
                if args.base
                else [LineRange(start=1, end=sys.maxsize)]
            )
            statement = metric_for_changed_lines(details, 'statements', ranges)
            line = metric_for_changed_lines(details, 'lines', ranges)
            function = metric_for_changed_lines(details, 'functions', ranges)
            branch = metric_for_changed_lines(details, 'branches', ranges)
        except (RuntimeError, TypeError) as error:
            failed = True
            print(f'FAIL {display_path}: {error}')
            continue
        checks = [
            ('statements', statement, STATEMENT_THRESHOLD),
            ('functions', function, FUNCTION_THRESHOLD),
            ('lines', line, LINE_THRESHOLD),
            ('branches', branch, BRANCH_THRESHOLD),
        ]
        passed = all(value.percent >= threshold for _, value, threshold in checks)
        failed |= not passed
        label = 'PASS' if passed else 'FAIL'
        print(
            f'{label} {display_path}: '
            + '; '.join(render_metric(name, value) for name, value, _ in checks)
            + ('; branches N/A (no branch arcs)' if branch.total == 0 else '')
        )

    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())

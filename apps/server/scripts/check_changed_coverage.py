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
        arcs_by_file = load_arcs(args.data_file)
    except (RuntimeError, TypeError) as error:
        print(f'Coverage gate cannot run: {error}', file=sys.stderr)
        return 2

    failed = False
    print(
        'Python denominators: statements and lines both use Coverage.py executable '
        'source lines (the tracer cannot distinguish multiple statements on one line); '
        'functions are named def/async def entries observed as a negative-start arc into '
        'their first executable body statement; abstract/overload and declaration-only stubs '
        'are excluded; branches use Coverage.py possible/executed arcs.'
    )
    for path in eligible:
        display_path = path.relative_to(root)
        details = report_files.get(path)
        arcs = arcs_by_file.get(path)
        if details is None or arcs is None:
            failed = True
            missing: list[str] = []
            if details is None:
                missing.append('JSON report')
            if arcs is None:
                missing.append('arc data')
            print(f'FAIL {display_path}: missing from {" and ".join(missing)}')
            continue

        summary = details.get('summary', {})
        statement_total = int(summary.get('num_statements', 0))
        line_covered = int(summary.get('covered_lines', 0))
        statement = metric(line_covered, statement_total)
        line = metric(line_covered, statement_total)

        functions = function_entries(path)
        function_covered = sum(
            has_function_entry_arc(entry, arcs) for entry in functions
        )
        function = metric(function_covered, len(functions))

        branch_total = int(summary.get('num_branches', 0))
        branch_covered = int(summary.get('covered_branches', 0))
        branch = metric(branch_covered, branch_total)
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

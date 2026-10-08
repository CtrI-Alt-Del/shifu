"""Combine per-shard mutation reports into a pull-request summary."""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import json
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

CATEGORIES = ('killed', 'survived', 'uncovered', 'timeouts', 'errors')
DEFAULT_THRESHOLDS = Path(__file__).with_name('mutation_score_thresholds.json')


def category_for_status(status: str) -> str:
    normalized = re.sub(r'[_-]+', ' ', status.strip().lower())
    if normalized == 'killed':
        return 'killed'
    if normalized == 'survived':
        return 'survived'
    if 'no test' in normalized or 'uncovered' in normalized:
        return 'uncovered'
    if 'timeout' in normalized or 'timed out' in normalized:
        return 'timeouts'
    return 'errors'


def escape_table_cell(value: str) -> str:
    return (
        value.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('|', r'\|')
        .replace('\n', ' ')
        .replace('\r', ' ')
    )


def display_module(module: str) -> str:
    acronyms = {'mrp', 'pdv', 'pos', 'crm', 'erp'}
    return (
        module.upper()
        if module.lower() in acronyms
        else module.replace('_', ' ').title()
    )


def read_json_object(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        raw: object = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None, f'invalid {path.name}'
    if not isinstance(raw, dict):
        return None, f'invalid {path.name}'
    raw_mapping = cast('dict[object, object]', raw)
    if any(not isinstance(key, str) for key in raw_mapping):
        return None, f'invalid {path.name}'
    return cast('dict[str, object]', raw_mapping), None


def aggregate_module_counts(
    counts: object,
) -> tuple[dict[str, int] | None, str | None]:
    if not isinstance(counts, dict):
        return None, 'invalid module results'
    raw_counts = cast('dict[object, object]', counts)
    aggregate: dict[str, int] = dict.fromkeys(CATEGORIES, 0)
    for status, count in raw_counts.items():
        if status == 'total':
            continue
        if (
            not isinstance(status, str)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            return None, 'invalid module outcome count'
        aggregate[category_for_status(status)] += count
    total = raw_counts.get('total')
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or total < 0
        or sum(aggregate.values()) != total
    ):
        return None, 'module outcome totals do not match'
    return aggregate, None


def load_named_counts(
    raw: object, *, key_prefix: str | None, error_message: str
) -> tuple[dict[str, dict[str, int]], str | None]:
    if not isinstance(raw, dict):
        return {}, error_message

    results: dict[str, dict[str, int]] = {}
    for name, counts in cast('dict[object, object]', raw).items():
        if not isinstance(name, str) or (
            key_prefix is not None and not name.startswith(key_prefix)
        ):
            return {}, error_message
        aggregate, error = aggregate_module_counts(counts)
        if error is not None or aggregate is None:
            return {}, error or error_message
        results[name] = aggregate
    return results, None


def load_module_results(
    report_path: Path,
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]], str | None]:
    payload, error = read_json_object(report_path)
    if error is not None or payload is None:
        return {}, {}, error or 'invalid module-results.json'
    if payload.get('status') != 'complete' or payload.get('results_exit_code') != 0:
        return {}, {}, 'module results export failed'

    modules, error = load_named_counts(
        payload.get('modules'), key_prefix=None, error_message='invalid module results'
    )
    if error is not None:
        return {}, {}, error
    files, error = load_named_counts(
        payload.get('files', {}),
        key_prefix='src/shifu/',
        error_message='invalid file results',
    )
    return (modules, files, None) if error is None else ({}, {}, error)


def load_shard(
    report_dir: Path,
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]], str | None]:
    module_report = report_dir / 'module-results.json'
    if module_report.is_file():
        return load_module_results(module_report)

    selection = report_dir / 'selection.json'
    if not selection.is_file():
        return {}, {}, 'module results missing'
    payload, error = read_json_object(selection)
    if error is not None or payload is None:
        return {}, {}, error or 'invalid selection.json'
    if payload.get('status') == 'not-applicable' and not payload.get('mutate'):
        return {}, {}, None
    return {}, {}, 'module results missing'


def load_thresholds(
    path: Path,
) -> tuple[Fraction, Fraction, dict[str, Fraction]]:
    payload, error = read_json_object(path)
    if error is not None or payload is None:
        raise ValueError(error or f'invalid {path.name}')

    minimum = payload.get('minimum_new_code_score_percent')
    if (
        not isinstance(minimum, (int, float))
        or isinstance(minimum, bool)
        or not 0 <= minimum <= 100
    ):
        raise ValueError('invalid minimum new-code mutation score')

    tolerance = payload.get('regression_tolerance_percentage_points')
    if (
        not isinstance(tolerance, (int, float))
        or isinstance(tolerance, bool)
        or not 0 <= tolerance <= 100
    ):
        raise ValueError('invalid mutation score regression tolerance')

    raw_baselines = payload.get('module_baselines')
    if not isinstance(raw_baselines, dict):
        raise TypeError('invalid module score baselines')

    baselines: dict[str, Fraction] = {}
    for module, raw_baseline in cast('dict[object, object]', raw_baselines).items():
        if not isinstance(module, str) or not isinstance(raw_baseline, dict):
            raise TypeError('invalid module score baseline')
        values = cast('dict[object, object]', raw_baseline)
        killed = values.get('killed')
        scored = values.get('scored')
        if (
            not isinstance(killed, int)
            or isinstance(killed, bool)
            or not isinstance(scored, int)
            or isinstance(scored, bool)
            or scored <= 0
            or not 0 <= killed <= scored
        ):
            raise ValueError(f'invalid score counts for module {module}')
        baselines[module] = Fraction(killed, scored)

    return Fraction(str(minimum)) / 100, Fraction(str(tolerance)) / 100, baselines


def module_score(counts: Mapping[str, int]) -> Fraction | None:
    scored = counts['killed'] + counts['survived']
    return Fraction(counts['killed'], scored) if scored else None


def build_module_rows(
    modules: set[str],
    totals_by_module: dict[str, dict[str, int]],
    file_totals: dict[str, dict[str, int]],
    changed_sources: set[str],
    minimum_new_code_score: Fraction,
    regression_tolerance: Fraction,
    baselines: dict[str, Fraction],
    complete: bool,
) -> tuple[list[str], list[str], list[str]]:
    rows: list[str] = []
    regression_failures: list[str] = []
    new_code_failures: list[str] = []
    for module in sorted(modules, key=str.casefold):
        counts = totals_by_module[module]
        mutants = sum(counts.values())
        score = module_score(counts)
        baseline = baselines.get(module)
        regression_passed = baseline is None or (
            score is not None
            and score >= max(Fraction(0), baseline - regression_tolerance)
        )

        module_sources = {
            source for source in changed_sources if source_module(source) == module
        }
        new_counts = dict.fromkeys(CATEGORIES, 0)
        for source in module_sources:
            for category in CATEGORIES:
                new_counts[category] += file_totals.get(source, {}).get(category, 0)
        new_score = (
            module_score(cast('Mapping[str, int]', new_counts))
            if module_sources
            else None
        )
        new_code_passed = not module_sources or (
            new_score is not None and new_score >= minimum_new_code_score
        )

        if complete and not regression_passed:
            regression_failures.append(module)
        if complete and not new_code_passed:
            new_code_failures.append(module)
        passed = complete and regression_passed and new_code_passed
        score_display = f'{float(score * 100):.1f}%' if score is not None else 'N/A'
        result = 'PASS' if passed else 'FAIL' if complete else 'PENDING'
        rows.append(
            f'| {escape_table_cell(display_module(module))} | {mutants:,} | '
            f'{counts["killed"]:,} | {counts["survived"]:,} | '
            f'{counts["uncovered"]:,} | {counts["timeouts"]:,} | '
            f'{counts["errors"]:,} | {score_display} | {result} |'
        )
    return rows, regression_failures, new_code_failures


def source_module(source: str) -> str | None:
    parts = Path(source).parts
    if len(parts) >= 4 and parts[:2] == ('src', 'shifu'):
        return parts[2]
    return None


def changed_mutation_sources(path: Path | None) -> set[str]:
    if path is None:
        return set()
    prefix = 'apps/server/'
    return {
        source.removeprefix(prefix)
        for source in path.read_text().splitlines()
        if source.startswith(prefix)
        and '/core/use_cases/' in source
        and source.endswith('.py')
    }


def collect_report_counts(
    reports_dir: Path, expected_shards: int
) -> tuple[
    dict[str, dict[str, int]],
    dict[str, dict[str, int]],
    int,
    list[str],
]:
    modules: dict[str, dict[str, int]] = defaultdict(
        lambda: dict.fromkeys(CATEGORIES, 0)
    )
    files: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(CATEGORIES, 0))
    completed = 0
    incomplete: list[str] = []

    for shard in range(1, expected_shards + 1):
        artifact_dir = (
            reports_dir / f'server-mutation-shard-{shard}-of-{expected_shards}'
        )
        module_counts, file_counts, error = load_shard(artifact_dir)
        if error is not None:
            incomplete.append(f'{shard} ({error})')
            continue
        completed += 1
        for module, counts in module_counts.items():
            for category in CATEGORIES:
                modules[module][category] += counts[category]
        for source, counts in file_counts.items():
            for category in CATEGORIES:
                files[source][category] += counts[category]

    return modules, files, completed, incomplete


def mutation_score_summary(
    totals: Mapping[str, int], reports_complete: bool
) -> list[str]:
    if not reports_complete:
        return []
    scored = totals['killed'] + totals['survived']
    score = totals['killed'] / scored * 100 if scored else 0.0
    return [
        (
            f'**Final mutation score:** {score:.1f}% '
            f'({totals["killed"]:,} killed / {scored:,} covered mutants).'
        )
    ]


def gate_summary(
    complete: bool,
    reports_complete: bool,
    regression_failures: list[str],
    new_code_failures: list[str],
    incomplete: list[str],
) -> list[str]:
    if not complete:
        if reports_complete:
            return ['**Module score gate:** Not evaluated because mutation failed.']
        if incomplete:
            return ['**Incomplete shards:** ' + ', '.join(incomplete) + '.']
        return []

    failures: list[str] = []
    if regression_failures:
        failures.append(
            'existing score regression: '
            + ', '.join(display_module(module) for module in regression_failures)
        )
    if new_code_failures:
        failures.append(
            'new code below minimum: '
            + ', '.join(display_module(module) for module in new_code_failures)
        )
    if failures:
        return ['**Module score gate failed:** ' + '; '.join(failures) + '.']
    return ['**Module score gate:** Passed.']


def summarize_report(
    reports_dir: Path,
    expected_shards: int,
    mutation_result: str,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
    changed_files_path: Path | None = None,
) -> tuple[str, bool]:
    minimum_new_code_score, regression_tolerance, baselines = load_thresholds(
        thresholds_path
    )
    totals_by_module, file_totals, completed_shards, incomplete = collect_report_counts(
        reports_dir, expected_shards
    )
    reports_complete = completed_shards == expected_shards
    complete = reports_complete and mutation_result == 'success'
    totals = dict.fromkeys(CATEGORIES, 0)
    for counts in totals_by_module.values():
        for category in CATEGORIES:
            totals[category] += counts[category]

    changed_sources = changed_mutation_sources(changed_files_path)
    modules_to_report = (
        set(totals_by_module)
        | set(baselines)
        | {
            module
            for source in changed_sources
            if (module := source_module(source)) is not None
        }
    )
    module_rows, regression_failures, new_code_failures = build_module_rows(
        modules_to_report,
        totals_by_module,
        file_totals,
        changed_sources,
        minimum_new_code_score,
        regression_tolerance,
        baselines,
        complete,
    )

    rows = [
        '<!-- shifu-mutation-summary -->',
        '### Core use-case mutation results',
        '',
        (
            f'**Status:** {"Complete" if complete else "Reports complete" if reports_complete else "Incomplete"} '
            f'({completed_shards}/{expected_shards} shard reports; mutation job: {mutation_result}).'
        ),
        '',
        '| Module | Mutants | Killed | Survived | Uncovered | Timeouts | Errors | Score | Result |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |',
    ]

    rows.extend(module_rows)

    total_mutants = sum(totals.values())
    total_values = [total_mutants, *(totals[category] for category in CATEGORIES)]
    rows.append(
        '| **Total** | ' + ' | '.join(f'**{value:,}**' for value in total_values) + ' |'
    )
    rows.append('')

    rows.extend(
        mutation_score_summary(cast('Mapping[str, int]', totals), reports_complete)
    )
    rows.extend(
        [
            '',
            (
                f'[Download shard reports](https://github.com/{os.environ.get("GITHUB_REPOSITORY", "repository")}'
                f'/actions/runs/{os.environ.get("GITHUB_RUN_ID", "run")}).'
            ),
        ]
    )
    gate_lines = gate_summary(
        complete,
        reports_complete,
        regression_failures,
        new_code_failures,
        incomplete,
    )
    if gate_lines:
        rows.extend(['', *gate_lines])

    return '\n'.join(
        rows
    ), complete and not regression_failures and not new_code_failures


def summarize(
    reports_dir: Path,
    expected_shards: int,
    mutation_result: str,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
    changed_files_path: Path | None = None,
) -> str:
    report, _ = summarize_report(
        reports_dir,
        expected_shards,
        mutation_result,
        thresholds_path,
        changed_files_path,
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports-dir', type=Path, required=True)
    parser.add_argument('--expected-shards', type=int, required=True)
    parser.add_argument('--mutation-result', required=True)
    parser.add_argument('--thresholds', type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument('--changed-files', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--enforce', action='store_true')
    arguments = parser.parse_args()
    try:
        report, passed = summarize_report(
            arguments.reports_dir,
            arguments.expected_shards,
            arguments.mutation_result,
            arguments.thresholds,
            arguments.changed_files,
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    arguments.output.write_text(report + '\n')
    return 1 if arguments.enforce and not passed else 0


if __name__ == '__main__':
    raise SystemExit(main())

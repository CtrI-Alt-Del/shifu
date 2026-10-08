"""Combine per-shard mutation reports into a pull-request summary."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
from typing import cast

CATEGORIES = ('killed', 'survived', 'uncovered', 'timeouts', 'errors')


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


def load_module_results(
    report_path: Path,
) -> tuple[dict[str, dict[str, int]], str | None]:
    payload, error = read_json_object(report_path)
    if error is not None or payload is None:
        return {}, error or 'invalid module-results.json'
    if payload.get('status') != 'complete' or payload.get('results_exit_code') != 0:
        return {}, 'module results export failed'

    raw_modules = payload.get('modules')
    if not isinstance(raw_modules, dict):
        return {}, 'invalid module results'
    module_mapping = cast('dict[object, object]', raw_modules)

    modules: dict[str, dict[str, int]] = {}
    for module, counts in module_mapping.items():
        if not isinstance(module, str):
            return {}, 'invalid module results'
        aggregate, error = aggregate_module_counts(counts)
        if error is not None or aggregate is None:
            return {}, error or 'invalid module results'
        modules[module] = aggregate
    return modules, None


def load_shard(report_dir: Path) -> tuple[dict[str, dict[str, int]], str | None]:
    module_report = report_dir / 'module-results.json'
    if module_report.is_file():
        return load_module_results(module_report)

    selection = report_dir / 'selection.json'
    if not selection.is_file():
        return {}, 'module results missing'
    payload, error = read_json_object(selection)
    if error is not None or payload is None:
        return {}, error or 'invalid selection.json'
    if payload.get('status') == 'not-applicable' and not payload.get('mutate'):
        return {}, None
    return {}, 'module results missing'


def summarize(reports_dir: Path, expected_shards: int, mutation_result: str) -> str:
    totals_by_module: dict[str, dict[str, int]] = defaultdict(
        lambda: dict.fromkeys(CATEGORIES, 0)
    )
    completed_shards = 0
    incomplete: list[str] = []

    for shard in range(1, expected_shards + 1):
        artifact_dir = (
            reports_dir / f'server-mutation-shard-{shard}-of-{expected_shards}'
        )
        module_counts, error = load_shard(artifact_dir)
        if error is not None:
            incomplete.append(f'{shard} ({error})')
            continue
        completed_shards += 1
        for module, counts in module_counts.items():
            for category in CATEGORIES:
                totals_by_module[module][category] += counts[category]

    reports_complete = completed_shards == expected_shards
    complete = reports_complete and mutation_result == 'success'
    totals = dict.fromkeys(CATEGORIES, 0)
    for counts in totals_by_module.values():
        for category in CATEGORIES:
            totals[category] += counts[category]

    rows = [
        '<!-- shifu-mutation-summary -->',
        '### Core use-case mutation results',
        '',
        (
            f'**Status:** {"Complete" if complete else "Reports complete" if reports_complete else "Incomplete"} '
            f'({completed_shards}/{expected_shards} shard reports; mutation job: {mutation_result}).'
        ),
        '',
        '| Module | Mutants | Killed | Survived | Uncovered | Timeouts | Errors |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]

    for module in sorted(totals_by_module, key=str.casefold):
        counts = totals_by_module[module]
        mutants = sum(counts.values())
        values = [mutants, *(counts[category] for category in CATEGORIES)]
        rows.append(
            f'| {escape_table_cell(display_module(module))} | '
            + ' | '.join(map(str, values))
            + ' |'
        )

    total_mutants = sum(totals.values())
    total_values = [total_mutants, *(totals[category] for category in CATEGORIES)]
    rows.append(
        '| **Total** | ' + ' | '.join(f'**{value:,}**' for value in total_values) + ' |'
    )
    rows.append('')

    if reports_complete:
        scored = totals['killed'] + totals['survived']
        score = totals['killed'] / scored * 100 if scored else 0.0
        rows.append(
            f'**Final mutation score:** {score:.1f}% '
            f'({totals["killed"]:,} killed / {scored:,} covered mutants).'
        )
    elif incomplete:
        rows.append('**Incomplete shards:** ' + ', '.join(incomplete) + '.')

    rows.extend(
        [
            '',
            (
                f'[Download shard reports](https://github.com/{os.environ.get("GITHUB_REPOSITORY", "repository")}'
                f'/actions/runs/{os.environ.get("GITHUB_RUN_ID", "run")}).'
            ),
        ]
    )
    return '\n'.join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports-dir', type=Path, required=True)
    parser.add_argument('--expected-shards', type=int, required=True)
    parser.add_argument('--mutation-result', required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    arguments.output.write_text(
        summarize(
            arguments.reports_dir, arguments.expected_shards, arguments.mutation_result
        )
        + '\n'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Tests for the aggregate pull-request mutation report."""

import json
from pathlib import Path

from scripts.summarize_mutation_reports import changed_mutation_sources, summarize


def write_shard(reports: Path, shard: int, payload: dict[str, object]) -> None:
    directory = reports / f'server-mutation-shard-{shard}-of-2'
    directory.mkdir(parents=True)
    (directory / 'module-results.json').write_text(json.dumps(payload))


def test_changed_mutation_sources_ignores_ineligible_package_files(tmp_path: Path):
    changed_files = tmp_path / 'changed-files.txt'
    changed_files.write_text(
        '\n'.join(
            (
                'apps/server/src/shifu/learning/core/use_cases/__init__.py',
                'apps/server/src/shifu/learning/core/use_cases/fakers/goal.py',
                'apps/server/src/shifu/learning/core/use_cases/generated/goal.py',
                'apps/server/src/shifu/learning/core/use_cases/add_goal_use_case.py',
                'apps/server/src/shifu/learning/rest/router.py',
            )
        )
    )

    assert changed_mutation_sources(changed_files) == {
        'src/shifu/learning/core/use_cases/add_goal_use_case.py'
    }


def test_summarize_combines_outcomes_and_calculates_covered_score(tmp_path: Path):
    write_shard(
        tmp_path,
        1,
        {
            'status': 'complete',
            'results_exit_code': 0,
            'modules': {
                'learning': {
                    'total': 10,
                    'killed': 5,
                    'survived': 2,
                    'no tests': 2,
                    'timeout': 1,
                }
            },
        },
    )
    write_shard(
        tmp_path,
        2,
        {
            'status': 'complete',
            'results_exit_code': 0,
            'modules': {
                'identity': {'total': 2, 'killed': 1, 'survived': 1},
                'learning': {'total': 1, 'killed': 1},
            },
        },
    )

    report = summarize(tmp_path, expected_shards=2, mutation_result='success')

    assert '| Identity | 2 | 1 | 1 | 0 | 0 | 0 |' in report
    assert '| Learning | 11 | 6 | 2 | 2 | 1 | 0 |' in report
    assert '| **Total** | **13** | **7** | **3** | **2** | **1** | **0** |' in report
    assert '**Final mutation score:** 70.0%' in report
    assert '**Status:** Complete (2/2 shard reports; mutation job: success).' in report


def test_summarize_marks_missing_shards_incomplete_without_score(tmp_path: Path):
    report = summarize(tmp_path, expected_shards=2, mutation_result='failure')

    assert (
        '**Status:** Incomplete (0/2 shard reports; mutation job: failure).' in report
    )
    assert '**Final mutation score:**' not in report
    assert (
        '**Incomplete shards:** 1 (module results missing), 2 (module results missing).'
        in report
    )


def test_summarize_accepts_empty_not_applicable_shard(tmp_path: Path):
    directory = tmp_path / 'server-mutation-shard-1-of-2'
    directory.mkdir()
    (directory / 'selection.json').write_text(
        json.dumps({'mutate': [], 'tests': [], 'status': 'not-applicable'})
    )
    write_shard(
        tmp_path,
        2,
        {'status': 'complete', 'results_exit_code': 0, 'modules': {}},
    )

    report = summarize(tmp_path, expected_shards=2, mutation_result='success')

    assert '**Status:** Complete (2/2 shard reports; mutation job: success).' in report
    assert '**Final mutation score:** 0.0%' in report


def test_summarize_counts_unrecognized_mutmut_statuses_as_errors(tmp_path: Path):
    write_shard(
        tmp_path,
        1,
        {
            'status': 'complete',
            'results_exit_code': 0,
            'modules': {'learning': {'total': 1, 'unexpected status': 1}},
        },
    )
    write_shard(
        tmp_path,
        2,
        {'status': 'complete', 'results_exit_code': 0, 'modules': {}},
    )

    report = summarize(tmp_path, expected_shards=2, mutation_result='success')

    assert '| Learning | 1 | 0 | 0 | 0 | 0 | 1 |' in report


def test_summarize_keeps_score_when_reports_are_complete_but_job_failed(
    tmp_path: Path,
):
    write_shard(
        tmp_path,
        1,
        {
            'status': 'complete',
            'results_exit_code': 0,
            'modules': {'learning': {'total': 2, 'killed': 1, 'error': 1}},
        },
    )
    write_shard(
        tmp_path,
        2,
        {'status': 'complete', 'results_exit_code': 0, 'modules': {}},
    )

    report = summarize(tmp_path, expected_shards=2, mutation_result='failure')

    assert (
        '**Status:** Reports complete (2/2 shard reports; mutation job: failure).'
        in report
    )
    assert '| Learning | 2 | 1 | 0 | 0 | 0 | 1 |' in report
    assert '**Final mutation score:** 100.0%' in report

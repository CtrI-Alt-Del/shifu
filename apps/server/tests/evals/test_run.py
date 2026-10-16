from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, Any

from evals.run import EVAL_CLASSES, main

if TYPE_CHECKING:
    from pathlib import Path


class _FakeEvaluator:
    def __init__(self, selector: str, *, status: str = 'passed') -> None:
        self.selector = selector
        self.status = status
        self.arguments: tuple[str | None, str | None] | None = None
        self.closed = False

    def run(self, name: str | None = None, tag: str | None = None) -> dict[str, Any]:
        self.arguments = (name, tag)
        definitions = tuple(
            definition
            for eval_class in EVAL_CLASSES
            if eval_class.selector == self.selector
            for definition in eval_class.definitions()
            if (name is None or definition.name == name)
            and (tag is None or tag in definition.tags)
        )
        selected_ids = [definition.name for definition in definitions]
        return {
            'workflow': self.selector,
            'status': self.status,
            'selected_case_ids': selected_ids,
            'counts': {
                'selected': len(selected_ids),
                'passed': len(selected_ids) if self.status == 'passed' else 0,
                'failed': len(selected_ids) if self.status != 'passed' else 0,
                'skipped': 0,
            },
            'cases': [],
        }

    def close(self) -> None:
        self.closed = True


def test_list_uses_workflow_name_and_tag_without_building_dependencies(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()

    def fail_builder(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError('list must not build models')

    status = main(
        [
            '--workflow',
            'generate-mentor-title',
            '--name',
            'title_ignores_embedded_instruction',
            '--tag',
            'security',
            '--list',
            '--output-dir',
            str(tmp_path),
        ],
        evaluator_builder=fail_builder,
        stdout=stdout,
        stderr=io.StringIO(),
    )

    assert status == 0
    assert stdout.getvalue().splitlines() == [
        'generate-mentor-title\ttitle_ignores_embedded_instruction\tsecurity,task-fit'
    ]
    assert not tuple(tmp_path.iterdir())


def test_name_and_tag_selection_runs_only_matching_workflow_case(
    tmp_path: Path,
) -> None:
    built: list[str] = []
    instances: list[_FakeEvaluator] = []

    def builder(selector: str, *, mode: str) -> _FakeEvaluator:
        assert mode == 'double'
        built.append(selector)
        evaluator = _FakeEvaluator(selector)
        instances.append(evaluator)
        return evaluator

    status = main(
        [
            '--workflow',
            'process-mentor-response',
            '--name',
            'reviewer_rejects_unsupported_claim',
            '--tag',
            'security',
            '--output-dir',
            str(tmp_path),
        ],
        evaluator_builder=builder,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        environ={},
    )

    assert status == 0
    assert built == ['process-mentor-response']
    assert instances[0].arguments == (
        'reviewer_rejects_unsupported_claim',
        'security',
    )
    report = json.loads(
        (tmp_path / 'process-mentor-response.json').read_text(encoding='utf-8')
    )
    assert report['selected_scope']['case_ids'] == [
        'reviewer_rejects_unsupported_claim'
    ]
    assert report['selected_scope']['partial'] is True
    assert instances[0].closed is True


def test_no_workflow_selects_every_available_eval_class(tmp_path: Path) -> None:
    built: list[str] = []

    def builder(selector: str, *, mode: str) -> _FakeEvaluator:
        built.append(selector)
        return _FakeEvaluator(selector)

    status = main(
        ['--output-dir', str(tmp_path)],
        evaluator_builder=builder,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        environ={},
    )

    assert status == 0
    assert built == [eval_class.selector for eval_class in EVAL_CLASSES]
    assert (tmp_path / 'summary.json').exists()
    assert len(tuple(tmp_path.glob('*.json'))) == len(EVAL_CLASSES) + 1


def test_unknown_workflow_and_empty_or_unknown_case_return_two(
    tmp_path: Path,
) -> None:
    built: list[str] = []

    def builder(selector: str, *, mode: str) -> _FakeEvaluator:
        built.append(selector)
        return _FakeEvaluator(selector)

    unknown_status = main(
        ['--workflow', 'unknown-workflow', '--output-dir', str(tmp_path)],
        evaluator_builder=builder,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    empty_status = main(
        [
            '--workflow',
            'generate-mentor-title',
            '--tag',
            'unknown-tag',
            '--output-dir',
            str(tmp_path),
        ],
        evaluator_builder=builder,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    unknown_case_status = main(
        ['--name', 'missing-case', '--output-dir', str(tmp_path)],
        evaluator_builder=builder,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )

    assert unknown_status == empty_status == unknown_case_status == 2
    assert built == []
    assert not tuple(tmp_path.iterdir())


def test_failed_workflow_reports_are_aggregated_and_exit_one(tmp_path: Path) -> None:
    built: list[str] = []

    def builder(selector: str, *, mode: str) -> _FakeEvaluator:
        built.append(selector)
        return _FakeEvaluator(
            selector,
            status='failed' if selector == 'evaluate-code-activity' else 'passed',
        )

    status = main(
        ['--output-dir', str(tmp_path)],
        evaluator_builder=builder,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        environ={},
    )

    assert status == 1
    assert len(built) == len(EVAL_CLASSES)
    summary = json.loads((tmp_path / 'summary.json').read_text(encoding='utf-8'))
    assert summary['exit_status'] == 1
    assert summary['workflows']['evaluate-code-activity']['status'] == 'failed'
    assert summary['workflows']['generate-mentor-title']['status'] == 'passed'


def test_builder_failure_writes_safe_failure_report(tmp_path: Path) -> None:
    stdout = io.StringIO()

    def fail_builder(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError('private prompt and synthetic-eval-only credential')

    status = main(
        [
            '--workflow',
            'generate-mentor-title',
            '--output-dir',
            str(tmp_path),
        ],
        evaluator_builder=fail_builder,
        stdout=stdout,
        stderr=io.StringIO(),
        environ={},
    )

    assert status == 1
    report_text = (tmp_path / 'generate-mentor-title.json').read_text(encoding='utf-8')
    summary_text = (tmp_path / 'summary.json').read_text(encoding='utf-8')
    assert 'eval_setup_failed' in report_text
    assert 'private prompt' not in report_text + summary_text
    assert 'credential' not in report_text + summary_text

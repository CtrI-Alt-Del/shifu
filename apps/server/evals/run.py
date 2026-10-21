from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.classify_learner_memory_eval import ClassifyLearnerMemoryEval
from evals.common import CaseDefinition, failed_setup_report
from evals.evaluate_code_activity_eval import EvaluateCodeActivityEval
from evals.generate_mentor_title_eval import GenerateMentorTitleEval
from evals.prepare_mentor_attachment_eval import PrepareMentorAttachmentEval
from evals.process_mentor_response_eval import ProcessMentorResponseEval
from evals.summarize_mentor_session_eval import SummarizeMentorSessionEval

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import TextIO


EVAL_CLASSES = (
    GenerateMentorTitleEval,
    EvaluateCodeActivityEval,
    ProcessMentorResponseEval,
    PrepareMentorAttachmentEval,
    SummarizeMentorSessionEval,
    ClassifyLearnerMemoryEval,
)
EVAL_BY_SELECTOR = {eval_class.selector: eval_class for eval_class in EVAL_CLASSES}
DEFAULT_OUTPUT_DIR = Path('test-results/evals')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run synthetic Shifu AI quality evals.'
    )
    parser.add_argument(
        '--workflow',
        action='append',
        dest='workflows',
        metavar='SELECTOR',
        help='Run one or more affected eval selectors. Defaults to the full catalogue.',
    )
    parser.add_argument(
        '--name', help='Run the named case within the selected workflows.'
    )
    parser.add_argument('--tag', help='Run cases carrying the selected tag.')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help='Directory for workflow JSON reports and summary.json.',
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List matching case IDs without constructing model dependencies.',
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    evaluator_builder: Callable[..., Any] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    environ: dict[str, str] | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as error:
        return 0 if error.code is None else int(error.code)

    matching, error_code = _select_matching(
        arguments.workflows,
        name=arguments.name,
        tag=arguments.tag,
    )
    if error_code is not None:
        print(error_code, file=err)
        return 2

    if arguments.list:
        _print_matching(matching, out)
        return 0

    env = os.environ if environ is None else environ
    mode = 'real' if env.get('SHIFU_RUN_REAL_AI_EVALS') == '1' else 'double'
    if evaluator_builder is None:
        from evals.dependencies import build_evaluator

        evaluator_builder = build_evaluator

    return _execute_selection(
        matching=matching,
        name=arguments.name,
        tag=arguments.tag,
        output_dir=arguments.output_dir,
        mode=mode,
        evaluator_builder=evaluator_builder,
        stdout=out,
        stderr=err,
    )


def _select_matching(
    workflows: list[str] | None,
    *,
    name: str | None,
    tag: str | None,
) -> tuple[dict[str, tuple[CaseDefinition, ...]], str | None]:
    if workflows is None:
        selectors = tuple(eval_class.selector for eval_class in EVAL_CLASSES)
    else:
        if any(selector not in EVAL_BY_SELECTOR for selector in workflows):
            return {}, 'unknown_workflow_selector'
        selectors = tuple(dict.fromkeys(workflows))

    matching: dict[str, tuple[CaseDefinition, ...]] = {}
    for selector in selectors:
        definitions = EVAL_BY_SELECTOR[selector].definitions()
        selected = tuple(
            definition
            for definition in definitions
            if (name is None or definition.name == name)
            and (tag is None or tag in definition.tags)
        )
        if selected:
            matching[selector] = selected
        elif workflows is not None:
            return {}, 'empty_eval_selection'
    if not matching:
        return {}, 'unknown_case_or_tag_or_empty_eval_selection'
    return matching, None


def _print_matching(
    matching: dict[str, tuple[CaseDefinition, ...]], output: TextIO
) -> None:
    for selector, definitions in matching.items():
        for definition in definitions:
            print(
                f'{selector}\t{definition.name}\t{",".join(definition.tags)}',
                file=output,
            )


def _execute_selection(
    *,
    matching: dict[str, tuple[CaseDefinition, ...]],
    name: str | None,
    tag: str | None,
    output_dir: Path,
    mode: str,
    evaluator_builder: Callable[..., Any],
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    reports: dict[str, dict[str, Any]] = {}
    report_write_failed = False
    for selector, selected in matching.items():
        definitions = EVAL_BY_SELECTOR[selector].definitions()
        report = _run_one(
            selector=selector,
            selected=selected,
            definitions=definitions,
            name=name,
            tag=tag,
            mode=mode,
            evaluator_builder=evaluator_builder,
        )
        report['mode'] = mode
        report['selected_scope'] = {
            'workflow': selector,
            'case_ids': [definition.name for definition in selected],
            'partial': len(selected) < len(definitions),
        }
        reports[selector] = report
        try:
            _write_json(output_dir / f'{selector}.json', report)
        except OSError:
            report_write_failed = True
            print('report_write_failed', file=stderr)

    summary = _make_summary(matching, reports, mode, report_write_failed)
    exit_code = summary['exit_status']
    try:
        _write_json(output_dir / 'summary.json', summary)
    except OSError:
        print('report_write_failed', file=stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, separators=(',', ':')), file=stdout)
    return exit_code


def _run_one(
    *,
    selector: str,
    selected: tuple[CaseDefinition, ...],
    definitions: tuple[CaseDefinition, ...],
    name: str | None,
    tag: str | None,
    mode: str,
    evaluator_builder: Callable[..., Any],
) -> dict[str, Any]:
    try:
        evaluator = evaluator_builder(selector, mode=mode)
        try:
            return evaluator.run(name=name, tag=tag)
        finally:
            _close_evaluator(evaluator)
    except Exception:  # noqa: BLE001 - provider/setup errors may contain synthetic or private inputs.
        return failed_setup_report(
            workflow=selector,
            definitions=definitions,
            selected=selected,
            mode=mode,
            model_profile='unavailable',
        )


def _make_summary(
    matching: dict[str, tuple[CaseDefinition, ...]],
    reports: dict[str, dict[str, Any]],
    mode: str,
    report_write_failed: bool,
) -> dict[str, Any]:
    all_passed = all(report.get('status') == 'passed' for report in reports.values())
    exit_code = 0 if all_passed and not report_write_failed else 1
    return {
        'status': 'passed' if exit_code == 0 else 'failed',
        'exit_status': exit_code,
        'mode': mode,
        'selected_scope': {
            'workflows': list(matching),
            'case_ids': {
                selector: [definition.name for definition in definitions]
                for selector, definitions in matching.items()
            },
            'partial': any(
                len(definitions) < len(EVAL_BY_SELECTOR[selector].definitions())
                for selector, definitions in matching.items()
            ),
        },
        'failure_code': 'report_write_failed' if report_write_failed else None,
        'workflows': {
            selector: {
                'status': report.get('status'),
                'selected_case_ids': report.get('selected_case_ids', []),
                'counts': report.get('counts', {}),
                'failure_code': report.get('failure_code'),
            }
            for selector, report in reports.items()
        },
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.tmp')
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    temporary.replace(path)


def _close_evaluator(evaluator: Any) -> None:
    close = getattr(evaluator, 'close', None)
    if callable(close):
        close()


if __name__ == '__main__':
    raise SystemExit(main())

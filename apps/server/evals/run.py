from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.classify_learner_memory_eval import ClassifyLearnerMemoryEval
from evals.classify_mentor_intent_eval import ClassifyMentorIntentEval
from evals.classify_planning_intent_eval import ClassifyPlanningIntentEval
from evals.generate_mentor_title_eval import GenerateMentorTitleEval
from evals.plan_goal_interview_eval import PlanGoalInterviewEval
from evals.plan_goal_proposal_eval import PlanGoalProposalEval
from evals.prepare_mentor_attachment_eval import PrepareMentorAttachmentEval
from evals.process_mentor_response_eval import ProcessMentorResponseEval
from evals.retrieve_planning_skills_eval import (
    RetrievePlanningSkillsE5Eval,
    RetrievePlanningSkillsEval,
)
from evals.summarize_mentor_session_eval import SummarizeMentorSessionEval

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import TextIO

    from evals.eval import Eval


EVAL_CLASSES = (
    GenerateMentorTitleEval,
    ProcessMentorResponseEval,
    PrepareMentorAttachmentEval,
    SummarizeMentorSessionEval,
    ClassifyLearnerMemoryEval,
    ClassifyMentorIntentEval,
    ClassifyPlanningIntentEval,
    RetrievePlanningSkillsEval,
    RetrievePlanningSkillsE5Eval,
    PlanGoalInterviewEval,
    PlanGoalProposalEval,
)
EVAL_BY_SELECTOR = {eval_class.selector: eval_class for eval_class in EVAL_CLASSES}
DEFAULT_OUTPUT_DIR = Path('test-results/evals')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run Shifu AI quality evals.')
    parser.add_argument(
        '--workflow',
        action='append',
        dest='workflows',
        metavar='SELECTOR',
        help='Run one or more eval selectors. Defaults to the full catalogue.',
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
        help='List matching case IDs (evals are built in double mode, no model call).',
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
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

    if arguments.workflows is None:
        selectors = tuple(EVAL_BY_SELECTOR)
    elif any(selector not in EVAL_BY_SELECTOR for selector in arguments.workflows):
        print('unknown_workflow_selector', file=err)
        return 2
    else:
        selectors = tuple(dict.fromkeys(arguments.workflows))

    env = os.environ if environ is None else environ
    real = env.get('SHIFU_RUN_REAL_AI_EVALS') == '1' and not arguments.list
    mode = 'real' if real else 'double'

    evaluators, matching = _build_and_select(
        selectors, mode=mode, name=arguments.name, tag=arguments.tag
    )
    error_code = _selection_error(
        matching, explicit=arguments.workflows is not None, expected=len(selectors)
    )
    if error_code is not None:
        _close_all(evaluators)
        print(error_code, file=err)
        return 2

    if arguments.list:
        for selector, selected in matching.items():
            for case in selected:
                print(f'{selector}\t{case.name}\t{",".join(case.tags)}', file=out)
        _close_all(evaluators)
        return 0

    return _execute(
        evaluators=evaluators,
        matching=matching,
        output_dir=arguments.output_dir,
        mode=mode,
        stdout=out,
        stderr=err,
    )


def _selection_error(
    matching: dict[str, tuple[Any, ...]], *, explicit: bool, expected: int
) -> str | None:
    if not matching:
        return 'unknown_case_or_tag_or_empty_eval_selection'
    if explicit and len(matching) < expected:
        return 'empty_eval_selection'
    return None


def _close_all(evaluators: dict[str, Eval | None]) -> None:
    for evaluator in evaluators.values():
        if evaluator is not None:
            evaluator.close()


def _build_and_select(
    selectors: tuple[str, ...], *, mode: str, name: str | None, tag: str | None
) -> tuple[dict[str, Eval | None], dict[str, tuple[Any, ...]]]:
    """Build each eval once; a failed build keeps its selector with no evaluator."""
    evaluators: dict[str, Eval | None] = {}
    matching: dict[str, tuple[Any, ...]] = {}
    for selector in selectors:
        try:
            evaluator = EVAL_BY_SELECTOR[selector](mode=mode)
        except Exception:  # noqa: BLE001 - setup errors may contain private configuration.
            evaluators[selector] = None
            matching[selector] = ()
            continue
        evaluators[selector] = evaluator
        selected = evaluator.select(name=name, tag=tag)
        if selected:
            matching[selector] = selected
        else:
            evaluator.close()
            evaluators[selector] = None
    return evaluators, matching


def _execute(
    *,
    evaluators: dict[str, Eval | None],
    matching: dict[str, tuple[Any, ...]],
    output_dir: Path,
    mode: str,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    reports: dict[str, dict[str, Any]] = {}
    report_write_failed = False
    for selector, selected in matching.items():
        evaluator = evaluators[selector]
        if evaluator is None:
            report = _unbuilt_report(selector, mode)
        else:
            try:
                report = evaluator.run(selected)
            except Exception:  # noqa: BLE001 - provider errors may contain private inputs.
                report = evaluator.setup_failed_report(selected)
            finally:
                evaluator.close()
        report['selected_scope'] = {
            'workflow': selector,
            'case_ids': [case.name for case in selected],
            'partial': report.get('partial', False),
        }
        reports[selector] = report
        try:
            _write_json(output_dir / f'{selector}.json', report)
        except OSError:
            report_write_failed = True
            print('report_write_failed', file=stderr)

    summary = _summary(reports, mode, report_write_failed)
    try:
        _write_json(output_dir / 'summary.json', summary)
    except OSError:
        print('report_write_failed', file=stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, separators=(',', ':')), file=stdout)
    return int(summary['exit_status'])


def _unbuilt_report(selector: str, mode: str) -> dict[str, Any]:
    return {
        'workflow': selector,
        'status': 'failed',
        'partial': False,
        'mode': mode,
        'model_profile': 'unavailable',
        'selected_case_ids': [],
        'counts': {'selected': 0, 'passed': 0, 'failed': 0, 'skipped': 0},
        'failure_code': 'eval_setup_failed',
        'cases': [],
    }


def _summary(
    reports: dict[str, dict[str, Any]], mode: str, report_write_failed: bool
) -> dict[str, Any]:
    all_passed = all(report.get('status') == 'passed' for report in reports.values())
    exit_code = 0 if all_passed and not report_write_failed else 1
    return {
        'status': 'passed' if exit_code == 0 else 'failed',
        'exit_status': exit_code,
        'mode': mode,
        'selected_scope': {
            'workflows': list(reports),
            'case_ids': {
                selector: report['selected_scope']['case_ids']
                for selector, report in reports.items()
            },
            'partial': any(
                report['selected_scope']['partial'] for report in reports.values()
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


if __name__ == '__main__':
    raise SystemExit(main())

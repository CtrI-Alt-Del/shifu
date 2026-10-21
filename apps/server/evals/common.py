from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from agno.eval import SuiteResult, run_cases
from shifu.intelligence.ai.agno.models.mentor_openai_chat import (
    mentor_transport_failure_scope,
)

DATASET_REVISION = 'mentor-attachments-synthetic-2026-10-14.2'
PROMPT_REVISION = 'mentor-attachments-eval-contract-v1'
DEFAULT_TIMEOUT_SECONDS = 90


@dataclass(frozen=True)
class CaseDefinition:
    name: str
    tags: tuple[str, ...]
    input: str
    expected: Any


class EmptySelectionError(ValueError):
    """Raised when a workflow selector matches no executable synthetic case."""


def select_definitions(
    definitions: tuple[CaseDefinition, ...],
    *,
    name: str | None,
    tag: str | None,
) -> tuple[CaseDefinition, ...]:
    selected = tuple(
        definition
        for definition in definitions
        if (name is None or definition.name == name)
        and (tag is None or tag in definition.tags)
    )
    if not selected:
        raise EmptySelectionError
    return selected


def normalize_suite(
    suite: SuiteResult,
    *,
    workflow: str,
    definitions: tuple[CaseDefinition, ...],
    selected: tuple[CaseDefinition, ...],
    mode: str,
    model_profile: str,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for result in suite.results:
        if result.skipped:
            outcome = 'skipped'
            failure_code = 'case_skipped'
        elif result.passed:
            outcome = 'passed'
            failure_code = None
        else:
            outcome = 'failed'
            failure_code = (
                'case_timed_out'
                if result.timed_out
                else 'case_error'
                if result.error
                else 'scorer_rejected'
            )
        cases.append(
            {
                'case_id': result.name,
                'outcome': outcome,
                'duration_seconds': round(max(result.duration_seconds, 0.0), 3),
                'skipped': result.skipped,
                'scorer_passed': result.passed if not result.skipped else None,
                'failure_code': failure_code,
            }
        )

    successful = bool(cases) and all(case['outcome'] == 'passed' for case in cases)
    return {
        'workflow': workflow,
        'status': 'passed' if successful else 'failed',
        'partial': len(selected) < len(definitions),
        'mode': mode,
        'model_profile': model_profile,
        'dataset_revision': DATASET_REVISION,
        'prompt_revision': PROMPT_REVISION,
        'selected_case_ids': [definition.name for definition in selected],
        'counts': {
            'selected': len(cases),
            'passed': sum(case['outcome'] == 'passed' for case in cases),
            'failed': sum(case['outcome'] == 'failed' for case in cases),
            'skipped': sum(case['outcome'] == 'skipped' for case in cases),
        },
        'cases': cases,
    }


def failed_setup_report(
    *,
    workflow: str,
    definitions: tuple[CaseDefinition, ...],
    selected: tuple[CaseDefinition, ...],
    mode: str,
    model_profile: str,
) -> dict[str, Any]:
    return {
        'workflow': workflow,
        'status': 'failed',
        'partial': len(selected) < len(definitions),
        'mode': mode,
        'model_profile': model_profile,
        'dataset_revision': DATASET_REVISION,
        'prompt_revision': PROMPT_REVISION,
        'selected_case_ids': [definition.name for definition in selected],
        'counts': {
            'selected': len(selected),
            'passed': 0,
            'failed': len(selected),
            'skipped': 0,
        },
        'failure_code': 'eval_setup_failed',
        'cases': [
            {
                'case_id': definition.name,
                'outcome': 'failed',
                'duration_seconds': 0.0,
                'skipped': False,
                'scorer_passed': False,
                'failure_code': 'eval_setup_failed',
            }
            for definition in selected
        ],
    }


def run_native_cases(
    cases: tuple[
        Any, ...
    ],  # Agno's Case annotations are incomplete in the installed SDK.
    *,
    definitions: tuple[CaseDefinition, ...],
    selected: tuple[CaseDefinition, ...],
    workflow: str,
    mode: str,
    model_profile: str,
) -> dict[str, Any]:
    try:
        with mentor_transport_failure_scope() as failure:
            suite = run_cases(cases, default_timeout=DEFAULT_TIMEOUT_SECONDS)
            failure.raise_if_failed()
    except Exception:  # noqa: BLE001 - exception text can include private input or credentials.
        return failed_setup_report(
            workflow=workflow,
            definitions=definitions,
            selected=selected,
            mode=mode,
            model_profile=model_profile,
        )
    return normalize_suite(
        suite,
        workflow=workflow,
        definitions=definitions,
        selected=selected,
        mode=mode,
        model_profile=model_profile,
    )


def close_agent(agent: Any) -> None:
    close = getattr(agent, 'close', None)
    if not callable(close):
        close = getattr(getattr(agent, 'model', None), 'close', None)
    if callable(close):
        with suppress(Exception):
            close()

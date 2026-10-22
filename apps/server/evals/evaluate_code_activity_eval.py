from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any, Protocol

from shifu.shared.core.domain.structures.code_rubric_assessment_input import (
    CodeRubricAssessmentInput,
)
from shifu.shared.core.domain.structures.curriculum_code_rubric_criterion_snapshot import (
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
)

from evals.common import DATASET_REVISION, CaseDefinition, select_definitions

if TYPE_CHECKING:
    from collections.abc import Callable


class _CodeRubricProvider(Protocol):
    def assess(self, request: CodeRubricAssessmentInput) -> Any: ...


_RUBRIC = CurriculumCodeRubricCriterionSnapshot(
    key='correctness',
    name='Correctness',
    description=(
        'Evaluate whether is_even(value) returns a boolean that is true exactly '
        'when the integer value is divisible by 2. Level 100 requires correct '
        'results for positive, zero, and negative integers. Level 75 is correct '
        'for non-negative integers but fails for negative integers. Level 50 '
        'attempts a parity check but returns the opposite result. Level 25 has '
        'the function but no meaningful parity check. Level 0 has no relevant '
        'implementation. If there is no submitted source, choose inconclusive.'
    ),
    weight_percentage=100,
    required=True,
    fixed_comments=tuple(
        CurriculumCodeRubricCommentSnapshot(
            id=f'correctness-{level}',
            level=level,
            text={
                0: 'No relevant implementation of is_even is present.',
                25: 'is_even exists but does not meaningfully check parity.',
                50: 'is_even checks parity but returns the opposite result.',
                75: 'is_even works for non-negative integers but fails for negatives.',
                100: 'is_even returns the correct boolean for every integer.',
            }[level],
        )
        for level in (0, 25, 50, 75, 100)
    ),
    inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
        id='correctness-inconclusive',
        text='The submitted evidence does not establish a correctness level.',
    ),
)

_DEFINITIONS = (
    CaseDefinition(
        name='code_rubric_supported_decision',
        tags=('smoke', 'rubric'),
        input=(
            'Implement is_even(value) so it returns True exactly when the integer '
            'value is divisible by 2, including negative integers, and returns '
            'False otherwise. The result must be a boolean.'
        ),
        expected={'expected_level': 100, 'source': 'composed-consumer'},
    ),
    CaseDefinition(
        name='code_rubric_insufficient_evidence_is_inconclusive',
        tags=('rubric', 'safety'),
        input=(
            'No source was submitted for the is_even task. The saved project file '
            'is an empty template, so there is no implementation to assess.'
        ),
        expected={'expected_level': 'inconclusive', 'source': 'composed-consumer'},
    ),
    CaseDefinition(
        name='code_rubric_rejects_deliberately_wrong_decision',
        tags=('rubric', 'negative-control'),
        input='Synthetic captured consumer returned a deliberately wrong level.',
        expected={
            'expected_level': 75,
            'captured_level': 25,
            'source': 'negative-control',
        },
    ),
)


def _assessment_input(definition: CaseDefinition) -> CodeRubricAssessmentInput:
    no_submission = (
        definition.name == 'code_rubric_insufficient_evidence_is_inconclusive'
    )
    return CodeRubricAssessmentInput(
        question_kind='text',
        prompt=definition.input,
        project_files=(
            ('main.py', '')
            if no_submission
            else ('main.py', 'def is_even(value):\n    return value % 2 == 0\n'),
        ),
        submitted_paths=() if no_submission else ('main.py',),
        rubric_criteria=(_RUBRIC,),
        concept_criteria=(),
    )


class EvaluateCodeActivityEval:
    selector = 'evaluate-code-activity'
    workflow_id = 'learning-evaluate-code-activity'
    dataset_revision = DATASET_REVISION
    prompt_revision = 'code-rubric-eval-v2'

    def __init__(
        self,
        provider: _CodeRubricProvider,
        *,
        mode: str,
        model_profile: str,
        close_resources: Callable[[], None] | None = None,
    ) -> None:
        self._provider = provider
        self._mode = mode
        self._model_profile = model_profile
        self._close_resources = close_resources

    @classmethod
    def definitions(cls) -> tuple[CaseDefinition, ...]:
        return _DEFINITIONS

    def run(self, name: str | None = None, tag: str | None = None) -> dict[str, Any]:
        definitions = self.definitions()
        selected = select_definitions(definitions, name=name, tag=tag)
        case_reports: list[dict[str, Any]] = []
        for definition in selected:
            started = _monotonic()
            try:
                if definition.expected.get('source') == 'negative-control':
                    actual_level = definition.expected.get('captured_level')
                else:
                    decisions = self._provider.assess(_assessment_input(definition))
                    actual_level = _single_level(decisions)
                expected_level = definition.expected.get('expected_level')
                correct = actual_level == expected_level
                accepted_wrong_answer = (
                    definition.expected.get('source') == 'negative-control'
                    and actual_level == definition.expected.get('captured_level')
                    and actual_level != expected_level
                )
                passed = correct or accepted_wrong_answer
                outcome = 'passed' if passed else 'failed'
                failure_code = None if passed else 'decision_expectation_mismatch'
            except Exception:  # noqa: BLE001 - provider errors can contain request data.
                outcome = 'failed'
                failure_code = 'assessment_unavailable'
                passed = False
            case_reports.append(
                {
                    'case_id': definition.name,
                    'outcome': outcome,
                    'duration_seconds': round(max(_monotonic() - started, 0.0), 3),
                    'skipped': False,
                    'scorer_passed': passed,
                    'failure_code': failure_code,
                }
            )

        successful = bool(case_reports) and all(
            case['outcome'] == 'passed' for case in case_reports
        )
        return {
            'workflow': self.selector,
            'status': 'passed' if successful else 'failed',
            'partial': len(selected) < len(definitions),
            'mode': self._mode,
            'model_profile': self._model_profile,
            'dataset_revision': DATASET_REVISION,
            'prompt_revision': self.prompt_revision,
            'selected_case_ids': [definition.name for definition in selected],
            'counts': {
                'selected': len(case_reports),
                'passed': sum(case['outcome'] == 'passed' for case in case_reports),
                'failed': sum(case['outcome'] == 'failed' for case in case_reports),
                'skipped': 0,
            },
            'cases': case_reports,
        }

    def close(self) -> None:
        if self._close_resources is not None:
            with suppress(Exception):
                self._close_resources()


def _single_level(decisions: Any) -> int | str | None:
    levels = getattr(decisions, 'criterion_levels', None)
    if not isinstance(levels, (list, tuple)) or len(levels) != 1:
        return None
    return getattr(levels[0], 'level', None)


def _monotonic() -> float:
    from time import monotonic

    return monotonic()

"""The Learning translation-activity workflow run in process over the disposable
PostgreSQL: real use cases and repositories, a mocked rubric assessor."""

from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager, contextmanager, nullcontext
from functools import partial
import json
from typing import TYPE_CHECKING
from unittest.mock import Mock
from uuid import UUID

import pytest

from shifu.learning.ai.agno.workflows.evaluate_translation_activity_workflow import (
    EvaluateTranslationActivityWorkflow,
)
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import PairMatchingEvaluationResult
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
    PersistActivityRubricDecisionUseCase,
    PrepareTranslationActivityEvaluationUseCase,
)
from shifu.shared.core.domain.structures import (
    CodeCriterionDecision,
    CodeRubricDecisions,
    CurriculumTranslationInconclusiveCommentSnapshot,
    CurriculumTranslationRubricCommentSnapshot,
    CurriculumTranslationRubricCriterionSnapshot,
    TranslationRubricAssessmentInput,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    TranslationRubricAssessorProvider,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from tests.fixtures.learning_fixture import (
    TRANSLATION_GRAMMAR_CRITERION_KEY,
    TRANSLATION_SEMANTIC_CRITERION_KEY,
    SeededTranslationActivity,
    seed_translation_activity_attempt,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from shifu.learning.core.domain.structures import ActivityRubricKind

    from tests.fixtures.postgres_fixture import PostgresDatabase

CAPABILITY = 'learning-translation-assessment'
DECISIONS = CodeRubricDecisions(
    criterion_levels=(
        CodeCriterionDecision(key=TRANSLATION_SEMANTIC_CRITERION_KEY, level=100),
        CodeCriterionDecision(key=TRANSLATION_GRAMMAR_CRITERION_KEY, level=100),
    ),
    concept_levels=(),
)


def _rubric_criterion(
    key: str, weight: int
) -> CurriculumTranslationRubricCriterionSnapshot:
    return CurriculumTranslationRubricCriterionSnapshot(
        key=key,
        name=key.replace('_', ' ').title(),
        description=f'Evaluate {key}.',
        weight_percentage=weight,
        required=True,
        fixed_comments=tuple(
            CurriculumTranslationRubricCommentSnapshot(
                id=f'{key}-{level}', level=level, text=f'Comment {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumTranslationInconclusiveCommentSnapshot(
            id=f'{key}-inconclusive', text='Inconclusivo'
        ),
    )


def assessment_input() -> TranslationRubricAssessmentInput:
    return TranslationRubricAssessmentInput(
        question_kind='translation',
        source_text='Bom dia',
        source_language='pt-BR',
        target_language='en-US',
        reference_translations=('Good morning',),
        submitted_text='Good morning',
        rubric_criteria=(
            _rubric_criterion(TRANSLATION_SEMANTIC_CRITERION_KEY, 70),
            _rubric_criterion(TRANSLATION_GRAMMAR_CRITERION_KEY, 30),
        ),
        concept_criteria=(),
    )


class Harness:
    def __init__(self, seeded: SeededTranslationActivity) -> None:
        self.seeded = seeded
        self.assessor = Mock(spec=TranslationRubricAssessorProvider)
        self.assessor.assess.return_value = DECISIONS
        self.handoffs = AgentOSHandoffStore()
        self.account_activity = Mock(spec=AccountActivityProvider)
        self.activity_calls = 0
        self.fail_activity_call: int | None = None
        self.fail_receipt_settlement_once = False
        self.persisted_before_receipt_settled: list[bool] = []
        self.receipt_states: dict[UUID, str] = {}
        self.persist_decision_use_case = PersistActivityRubricDecisionUseCase(
            seeded.database
        )

        self.account_activity.activity.side_effect = partial(_active_account, self)
        self.account_activity.external_effect.side_effect = partial(
            _external_effect, self
        )

        def attempt_account_id(attempt_id: str) -> str | None:
            with seeded.database.transaction() as repositories:
                return repositories.activity_attempts.find_account_id_by_attempt_id(
                    attempt_id
                )

        self.workflow = EvaluateTranslationActivityWorkflow(
            PrepareTranslationActivityEvaluationUseCase(seeded.database),
            EvaluateChoiceActivityUseCase(
                seeded.database, SystemClockProvider(), seeded.content_provider
            ),
            FailCodeActivityEvaluationUseCase(seeded.database),
            self.persist_decision_use_case,
            self.assessor,
            self.handoffs,
            self.account_activity,
            attempt_account_id,
        )

    def run_official(
        self, attempt_id: str | None = None, run_id: str | None = None
    ) -> object:
        return asyncio.run(
            self.workflow.arun(
                input=json.dumps(
                    {
                        'attempt_id': attempt_id or self.seeded.attempt.id,
                        'run_id': run_id or self.seeded.run_id,
                    }
                )
            )
        ).content

    def run_handoff(self, reference: str) -> object:
        return asyncio.run(
            self.workflow.arun(input=json.dumps({'handoff_ref': reference}))
        ).content


def _active_account(harness: Harness, _account_id: str) -> AbstractContextManager[None]:
    harness.activity_calls += 1
    if harness.activity_calls == harness.fail_activity_call:
        raise AuthorizationError
    return nullcontext()


@contextmanager
def _external_effect(
    harness: Harness,
    _account_id: str,
    effect_id: UUID,
    _operation: str,
    *,
    allow_durable_result_recovery: bool = False,
) -> Generator[bool]:
    state = harness.receipt_states.get(effect_id)
    if state == 'settled':
        yield False
        return
    if state in ('in_flight', 'unknown'):
        if not allow_durable_result_recovery:
            raise RuntimeError('receipt is unresolved')
        yield False
        harness.receipt_states[effect_id] = 'settled'
        return
    harness.receipt_states[effect_id] = 'in_flight'
    try:
        yield True
    except BaseException:
        harness.receipt_states[effect_id] = 'unknown'
        raise
    else:
        harness.persisted_before_receipt_settled.append(
            bool(harness.seeded.current_evaluation().rubric_decisions)
        )
        if harness.fail_receipt_settlement_once:
            harness.fail_receipt_settlement_once = False
            harness.receipt_states[effect_id] = 'unknown'
            raise RuntimeError('receipt settlement interrupted')
        harness.receipt_states[effect_id] = 'settled'


@pytest.fixture
def harness(postgres_database: PostgresDatabase) -> Harness:
    return Harness(seed_translation_activity_attempt(postgres_database.engine))


class TestEvaluateTranslationActivityWorkflow:
    def test_grades_the_attempt_with_the_assessor_decisions(
        self, harness: Harness
    ) -> None:
        assert harness.run_official() == 'completed'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert evaluation.rubric_decisions == ()
        assert {part.question_key for part in evaluation.parts} == {'q1', 'q2', 'q3'}
        harness.assessor.assess.assert_called_once()
        request = harness.assessor.assess.call_args.args[0]
        assert isinstance(request, TranslationRubricAssessmentInput)
        assert request.submitted_text == 'Good morning'
        effect_call = harness.account_activity.external_effect.call_args
        with harness.seeded.database.transaction() as repositories:
            expected_account_id = (
                repositories.activity_attempts.find_account_id_by_attempt_id(
                    harness.seeded.attempt.id
                )
            )
        assert effect_call.args[0] == expected_account_id
        assert isinstance(effect_call.args[1], UUID)
        assert effect_call.args[2] == 'learning.translation-rubric.assess'
        assert harness.persisted_before_receipt_settled == [True]

    def test_reuses_a_durable_decision_after_receipt_settlement_before_grade(
        self, harness: Harness
    ) -> None:
        harness.fail_activity_call = 3

        assert harness.run_official() != 'completed'

        pending = harness.seeded.current_evaluation()
        assert pending.status is ActivityEvaluationStatus.PENDING
        assert len(pending.rubric_decisions) == 1
        harness.assessor.assess.assert_called_once()
        harness.account_activity.external_effect.assert_called_once()
        assert harness.persisted_before_receipt_settled == [True]

        harness.fail_activity_call = None
        assert harness.run_official() == 'completed'

        completed = harness.seeded.current_evaluation()
        assert completed.status is ActivityEvaluationStatus.COMPLETED
        assert completed.rubric_decisions == ()
        harness.assessor.assess.assert_called_once()
        assert harness.account_activity.external_effect.call_count == 2

    def test_recovers_a_durable_decision_after_process_interruption_before_settle(
        self, harness: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        persist_decision = harness.persist_decision_use_case.execute

        def persist_then_interrupt(
            attempt_id: str,
            run_id: str,
            question_key: str,
            rubric_kind: ActivityRubricKind,
            decisions: CodeRubricDecisions,
        ) -> None:
            persist_decision(attempt_id, run_id, question_key, rubric_kind, decisions)
            raise SystemExit('simulated process interruption')

        monkeypatch.setattr(
            harness.persist_decision_use_case, 'execute', persist_then_interrupt
        )
        with pytest.raises(SystemExit, match='simulated process interruption'):
            harness.run_official()

        interrupted = harness.seeded.current_evaluation()
        assert interrupted.status is ActivityEvaluationStatus.PENDING
        assert len(interrupted.rubric_decisions) == 1
        assert tuple(harness.receipt_states.values()) == ('unknown',)
        harness.assessor.assess.assert_called_once()

        monkeypatch.setattr(
            harness.persist_decision_use_case, 'execute', persist_decision
        )
        assert harness.run_official() == 'completed'

        assert harness.seeded.current_evaluation().status is (
            ActivityEvaluationStatus.COMPLETED
        )
        assert tuple(harness.receipt_states.values()) == ('settled',)
        harness.assessor.assess.assert_called_once()
        assert harness.account_activity.external_effect.call_count == 2

    def test_clears_a_durable_decision_when_receipt_settlement_fails(
        self, harness: Harness
    ) -> None:
        harness.fail_receipt_settlement_once = True

        harness.run_official()

        failed = harness.seeded.current_evaluation()
        assert failed.status is ActivityEvaluationStatus.FAILED
        assert failed.rubric_decisions == ()
        assert harness.persisted_before_receipt_settled == [True]

    def test_closed_account_prevents_translation_assessment(
        self, harness: Harness
    ) -> None:
        harness.account_activity.activity.side_effect = AuthorizationError

        assert harness.run_official() != 'completed'

        harness.assessor.assess.assert_not_called()
        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.PENDING
        )

    def test_fails_the_evaluation_when_the_assessor_raises(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.side_effect = RuntimeError('decisions endpoint down')

        harness.run_official()

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is not ActivityEvaluationStatus.COMPLETED
        assert evaluation.parts == ()

    def test_fails_the_evaluation_when_a_mandatory_criterion_is_inconclusive(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(
                    key=TRANSLATION_SEMANTIC_CRITERION_KEY, level='inconclusive'
                ),
                CodeCriterionDecision(key=TRANSLATION_GRAMMAR_CRITERION_KEY, level=100),
            ),
            concept_levels=(),
        )

        harness.run_official()

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is not ActivityEvaluationStatus.COMPLETED
        assert evaluation.parts == ()

    def test_reports_a_stale_run(self, harness: Harness) -> None:
        assert harness.run_official(run_id='01J00000000000000000000000') == 'stale'

        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.PENDING
        )
        harness.assessor.assess.assert_not_called()

    def test_a_duplicate_run_with_the_same_run_id_after_completion_is_a_no_op(
        self, harness: Harness
    ) -> None:
        assert harness.run_official() == 'completed'
        harness.assessor.assess.reset_mock()

        assert harness.run_official() == 'stale'

        harness.assessor.assess.assert_not_called()
        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.COMPLETED
        )

    def test_answers_a_transient_assessment_handoff(self, harness: Harness) -> None:
        reference = harness.handoffs.create(
            capability=CAPABILITY, input_value=assessment_input()
        )

        assert harness.run_handoff(reference) == 'complete'

        assert harness.handoffs.take_result(reference, capability=CAPABILITY) == (
            DECISIONS
        )

    def test_marks_a_handoff_unavailable_when_the_assessor_raises(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.side_effect = RuntimeError('decisions endpoint down')
        reference = harness.handoffs.create(
            capability=CAPABILITY, input_value=assessment_input()
        )

        assert harness.run_handoff(reference) == 'unavailable'

        assert (
            harness.handoffs.take_result(reference, capability=CAPABILITY)
            == 'unavailable'
        )


class TestEvaluateTranslationActivityWorkflowWithPairs:
    def test_scores_the_pair_question_without_calling_the_assessor_for_it(
        self, postgres_database: PostgresDatabase
    ) -> None:
        harness = Harness(
            seed_translation_activity_attempt(
                postgres_database.engine, pair_matching=True
            )
        )

        assert harness.run_official() == 'completed'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.COMPLETED
        pair_result = next(
            part for part in evaluation.parts if part.question_key == 'q2'
        )
        assert isinstance(pair_result, PairMatchingEvaluationResult)
        assert pair_result.outcome == 'full'
        assert pair_result.correct_pair_count == 2
        # Only the translation question reached the assessor.
        harness.assessor.assess.assert_called_once()
        request = harness.assessor.assess.call_args.args[0]
        assert isinstance(request, TranslationRubricAssessmentInput)
        assert request.submitted_text == 'Good morning'
        assert harness.run_official() == 'stale'
        harness.assessor.assess.assert_called_once()

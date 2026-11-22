"""The Learning code-activity workflow run in process over the disposable
PostgreSQL: real use cases and repositories, a mocked rubric assessor."""

from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager, contextmanager, nullcontext
from functools import partial
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import TYPE_CHECKING
from unittest.mock import Mock
from uuid import UUID

import pytest

from shifu.learning.ai.agno.workflows.evaluate_code_activity_workflow import (
    EvaluateCodeActivityWorkflow,
)
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
    PersistActivityRubricDecisionUseCase,
    PrepareCodeActivityEvaluationUseCase,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.providers.account_activity.sqlalchemy_account_activity_provider import (
    SqlalchemyAccountActivityProvider,
)
from shifu.shared.core.domain.structures import (
    CodeCriterionDecision,
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    CodeRubricAssessorProvider,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from tests.fixtures.learning_fixture import (
    CODE_CRITERION_KEY,
    SeededCodeActivity,
    seed_code_activity_attempt,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from shifu.learning.core.domain.structures import ActivityRubricKind

    from tests.fixtures.postgres_fixture import PostgresDatabase

CAPABILITY = 'learning-code-assessment'
DECISIONS = CodeRubricDecisions(
    criterion_levels=(CodeCriterionDecision(key=CODE_CRITERION_KEY, level=100),),
    concept_levels=(),
)


def assessment_input() -> CodeRubricAssessmentInput:
    return CodeRubricAssessmentInput(
        question_kind='text',
        prompt='Implement is_even(value).',
        project_files=(
            ('main.py', 'def is_even(value):\n    return value % 2 == 0\n'),
        ),
        submitted_paths=('main.py',),
        rubric_criteria=(
            CurriculumCodeRubricCriterionSnapshot(
                key=CODE_CRITERION_KEY,
                name='Correctness',
                description='The function returns the right parity.',
                weight_percentage=100,
                required=True,
                fixed_comments=tuple(
                    CurriculumCodeRubricCommentSnapshot(
                        id=f'{CODE_CRITERION_KEY}-{level}',
                        level=level,
                        text=f'Level {level}.',
                    )
                    for level in (0, 25, 50, 75, 100)
                ),
                inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
                    id=f'{CODE_CRITERION_KEY}-inconclusive', text='Inconclusive.'
                ),
            ),
        ),
        concept_criteria=(),
    )


class Harness:
    def __init__(self, seeded: SeededCodeActivity) -> None:
        self.seeded = seeded
        self.assessor = Mock(spec=CodeRubricAssessorProvider)
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
        self.workflow = self.create_workflow(self.account_activity)

    def create_workflow(
        self, account_activity_provider: AccountActivityProvider
    ) -> EvaluateCodeActivityWorkflow:
        return EvaluateCodeActivityWorkflow(
            PrepareCodeActivityEvaluationUseCase(self.seeded.database, 262_144),
            EvaluateChoiceActivityUseCase(
                self.seeded.database,
                SystemClockProvider(),
                self.seeded.content_provider,
            ),
            FailCodeActivityEvaluationUseCase(self.seeded.database),
            self.persist_decision_use_case,
            self.assessor,
            self.handoffs,
            account_activity_provider,
            self._attempt_account_id,
        )

    def _attempt_account_id(self, attempt_id: str) -> str | None:
        with self.seeded.database.transaction() as repositories:
            return repositories.activity_attempts.find_account_id_by_attempt_id(
                attempt_id
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
    return Harness(seed_code_activity_attempt(postgres_database.engine))


class TestEvaluateCodeActivityWorkflow:
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
        assert isinstance(request, CodeRubricAssessmentInput)
        assert request.submitted_paths == ('src/main.js',)
        effect_call = harness.account_activity.external_effect.call_args
        with harness.seeded.database.transaction() as repositories:
            expected_account_id = (
                repositories.activity_attempts.find_account_id_by_attempt_id(
                    harness.seeded.attempt.id
                )
            )
        assert effect_call.args[0] == expected_account_id
        assert isinstance(effect_call.args[1], UUID)
        assert effect_call.args[2] == 'learning.code-rubric.assess'
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

    def test_overlapping_retry_and_original_run_settle_receipt_once(
        self, postgres_database: PostgresDatabase
    ) -> None:
        seeded = seed_code_activity_attempt(postgres_database.engine)
        identity_database = SqlalchemyIdentityDatabase(postgres_database.engine)
        account_activity = SqlalchemyAccountActivityProvider(
            identity_database, postgres_database.engine
        )
        assessor = Mock(spec=CodeRubricAssessorProvider)
        assessor.assess.return_value = DECISIONS
        original = Harness(seeded)
        retry = Harness(seeded)
        original.assessor = assessor
        retry.assessor = assessor
        original.workflow = original.create_workflow(account_activity)
        retry.workflow = retry.create_workflow(account_activity)
        persisted = Event()
        resume_original = Event()
        persist_decision = original.persist_decision_use_case.execute

        def persist_then_pause(
            attempt_id: str,
            run_id: str,
            question_key: str,
            rubric_kind: ActivityRubricKind,
            decisions: CodeRubricDecisions,
        ) -> None:
            persist_decision(attempt_id, run_id, question_key, rubric_kind, decisions)
            persisted.set()
            if not resume_original.wait(timeout=30):
                raise TimeoutError('original workflow was not released')

        original.persist_decision_use_case.execute = persist_then_pause
        with ThreadPoolExecutor(max_workers=1) as executor:
            original_run = executor.submit(original.run_official)
            try:
                assert persisted.wait(timeout=30)
                retry_result = retry.run_official()
            finally:
                resume_original.set()
            original_result = original_run.result(timeout=30)

        assert retry_result == 'completed'
        assert original_result in ('completed', 'stale')
        assessor.assess.assert_called_once()
        evaluation = seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert evaluation.rubric_decisions == ()
        with seeded.database.transaction() as repositories:
            account_id = repositories.activity_attempts.find_account_id_by_attempt_id(
                seeded.attempt.id
            )
        assert account_id is not None
        with identity_database.transaction() as repositories:
            assert (
                repositories.external_effect_receipts.has_unresolved_for_account_id(
                    account_id
                )
                is False
            )

    def test_clears_a_durable_decision_when_receipt_settlement_fails(
        self, harness: Harness
    ) -> None:
        harness.fail_receipt_settlement_once = True

        harness.run_official()

        failed = harness.seeded.current_evaluation()
        assert failed.status is ActivityEvaluationStatus.FAILED
        assert failed.rubric_decisions == ()
        assert harness.persisted_before_receipt_settled == [True]

    def test_closed_account_prevents_code_assessment(self, harness: Harness) -> None:
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

    def test_reports_a_stale_run(self, harness: Harness) -> None:
        assert harness.run_official(run_id='01J00000000000000000000000') == 'stale'

        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.PENDING
        )
        harness.assessor.assess.assert_not_called()

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

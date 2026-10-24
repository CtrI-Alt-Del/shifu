"""The Learning code-activity workflow run in process over the disposable
PostgreSQL: real use cases and repositories, a mocked rubric assessor."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from shifu.learning.ai.agno.workflows.evaluate_code_activity_workflow import (
    EvaluateCodeActivityWorkflow,
)
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
    PrepareCodeActivityEvaluationUseCase,
)
from shifu.shared.core.domain.structures import (
    CodeCriterionDecision,
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
)
from shifu.shared.core.interfaces import CodeRubricAssessorProvider
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from tests.fixtures.learning_fixture import (
    CODE_CRITERION_KEY,
    SeededCodeActivity,
    seed_code_activity_attempt,
)

if TYPE_CHECKING:
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
        self.workflow = EvaluateCodeActivityWorkflow(
            PrepareCodeActivityEvaluationUseCase(seeded.database, 262_144),
            EvaluateChoiceActivityUseCase(
                seeded.database, SystemClockProvider(), seeded.content_provider
            ),
            FailCodeActivityEvaluationUseCase(seeded.database),
            self.assessor,
            self.handoffs,
        )

    def run_official(
        self, attempt_id: str | None = None, run_id: str | None = None
    ) -> object:
        return self.workflow.run(
            json.dumps(
                {
                    'attempt_id': attempt_id or self.seeded.attempt.id,
                    'run_id': run_id or self.seeded.run_id,
                }
            )
        ).content

    def run_handoff(self, reference: str) -> object:
        return self.workflow.run(json.dumps({'handoff_ref': reference})).content


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
        assert {part.question_key for part in evaluation.parts} == {'q1', 'q2', 'q3'}
        harness.assessor.assess.assert_called_once()
        request = harness.assessor.assess.call_args.args[0]
        assert isinstance(request, CodeRubricAssessmentInput)
        assert request.submitted_paths == ('src/main.js',)

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

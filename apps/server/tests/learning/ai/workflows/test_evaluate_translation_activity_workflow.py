"""The Learning translation-activity workflow run in process over the disposable
PostgreSQL: real use cases and repositories, a mocked rubric assessor."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from shifu.learning.ai.agno.workflows.evaluate_translation_activity_workflow import (
    EvaluateTranslationActivityWorkflow,
)
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import PairMatchingEvaluationResult
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
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
from shifu.shared.core.interfaces import TranslationRubricAssessorProvider
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from tests.fixtures.learning_fixture import (
    TRANSLATION_GRAMMAR_CRITERION_KEY,
    TRANSLATION_SEMANTIC_CRITERION_KEY,
    SeededTranslationActivity,
    seed_translation_activity_attempt,
)

if TYPE_CHECKING:
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
        self.workflow = EvaluateTranslationActivityWorkflow(
            PrepareTranslationActivityEvaluationUseCase(seeded.database),
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
    return Harness(seed_translation_activity_attempt(postgres_database.engine))


class TestEvaluateTranslationActivityWorkflow:
    def test_grades_the_attempt_with_the_assessor_decisions(
        self, harness: Harness
    ) -> None:
        assert harness.run_official() == 'completed'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert {part.question_key for part in evaluation.parts} == {'q1', 'q2', 'q3'}
        harness.assessor.assess.assert_called_once()
        request = harness.assessor.assess.call_args.args[0]
        assert isinstance(request, TranslationRubricAssessmentInput)
        assert request.submitted_text == 'Good morning'

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

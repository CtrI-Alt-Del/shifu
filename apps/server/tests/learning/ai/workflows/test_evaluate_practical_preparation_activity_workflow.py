"""The Learning practical preparation workflow run in process over the disposable
PostgreSQL: real use cases and repositories, a mocked photo assessor port and an
in-memory photo storage."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from shifu.learning.ai.agno.workflows.evaluate_practical_preparation_activity_workflow import (
    EvaluatePracticalPreparationActivityWorkflow,
)
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import PracticalPreparationResult
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
    PreparePracticalPreparationActivityEvaluationUseCase,
    RetryChoiceEvaluationUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    PracticeCriterionDecision,
    PracticePhotoAssessmentInput,
    PracticePhotoDecisions,
    PracticeRecordDecision,
)
from shifu.shared.core.interfaces import PracticePhotoAssessorProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.learning_fixture import (
    SeededPracticalPreparationActivity,
    seed_practical_preparation_attempt,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoStorageStub

if TYPE_CHECKING:
    from tests.fixtures.postgres_fixture import PostgresDatabase

CUT = 'cut-regularity'
TECHNIQUE = 'observable-technique'
PRESENTATION = 'presentation'


def criterion(key: str, level: int | None) -> PracticeCriterionDecision:
    return PracticeCriterionDecision(
        key=key,
        level=level,  # pyright: ignore[reportArgumentType] - the use case checks allowed levels
        comment_key=f'{key}-{level}' if level is not None else None,
    )


def decisions(
    cut: int | None,
    technique: int | None,
    presentation: int | None,
    *,
    cuts_sufficient: bool = True,
) -> PracticePhotoDecisions:
    return PracticePhotoDecisions(
        criteria=(
            criterion(CUT, cut),
            criterion(TECHNIQUE, technique),
            criterion(PRESENTATION, presentation),
        ),
        records=(
            PracticeRecordDecision(record_key='cuts', sufficient=cuts_sufficient),
            PracticeRecordDecision(record_key='during', sufficient=True),
            PracticeRecordDecision(record_key='final', sufficient=True),
        ),
    )


class Harness:
    def __init__(self, postgres_database: PostgresDatabase) -> None:
        self.storage = PracticePhotoStorageStub()
        self.seeded: SeededPracticalPreparationActivity = (
            seed_practical_preparation_attempt(postgres_database.engine, self.storage)
        )
        self.assessor = Mock(spec=PracticePhotoAssessorProvider)
        self.assessor.assess.return_value = decisions(100, 50, 0)
        self.workflow = EvaluatePracticalPreparationActivityWorkflow(
            PreparePracticalPreparationActivityEvaluationUseCase(self.seeded.database),
            EvaluateChoiceActivityUseCase(
                self.seeded.database,
                SystemClockProvider(),
                self.seeded.content_provider,
            ),
            FailCodeActivityEvaluationUseCase(self.seeded.database),
            self.assessor,
            self.storage,
        )

    def run_official(self, run_id: str | None = None) -> object:
        return self.workflow.run(
            json.dumps(
                {
                    'attempt_id': self.seeded.attempt.id,
                    'run_id': run_id or self.seeded.run_id,
                }
            )
        ).content

    def request(self) -> PracticePhotoAssessmentInput:
        request = self.assessor.assess.call_args.args[0]
        assert isinstance(request, PracticePhotoAssessmentInput)
        return request


@pytest.fixture
def harness(postgres_database: PostgresDatabase) -> Harness:
    return Harness(postgres_database)


class TestEvaluatePracticalPreparationActivityWorkflow:
    def test_grades_the_attempt_with_the_weighted_levels(
        self, harness: Harness
    ) -> None:
        assert harness.run_official() == 'evaluated'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert evaluation.score == Decimal(60)
        (part,) = evaluation.parts
        assert isinstance(part, PracticalPreparationResult)
        assert [item.level for item in part.criterion_results] == [100, 50, 0]
        assert harness.seeded.concept_observation_values() == [Decimal(60)]

    def test_gives_the_assessor_only_the_rubric_and_the_photos_read_from_storage(
        self, harness: Harness
    ) -> None:
        harness.run_official()

        request = harness.request()
        assert [photo.record_key for photo in request.photos] == [
            'cuts',
            'during',
            'final',
        ]
        assert {photo.record_key: photo.content for photo in request.photos} == (
            harness.seeded.photo_bytes
        )
        assert [record.key for record in request.records] == [
            'cuts',
            'during',
            'final',
        ]
        assert [item.key for item in request.criteria] == [CUT, TECHNIQUE, PRESENTATION]
        flattened = repr(request)
        for identifier in (
            harness.seeded.attempt.id,
            harness.seeded.attempt.skill_experience_id,
            harness.seeded.attempt.activity_id,
            harness.seeded.run_id,
            'practice-photos/',
            'Os legumes ficaram firmes.',
        ):
            assert identifier not in flattened
        assert 'Refaça a foto dos cortes' not in flattened

    def test_keeps_the_photos_out_of_the_run_output(self, harness: Harness) -> None:
        output = harness.workflow.run(
            json.dumps(
                {
                    'attempt_id': harness.seeded.attempt.id,
                    'run_id': harness.seeded.run_id,
                }
            )
        )

        assert 'fake-png' not in repr(output)
        assert 'fake-png' not in str(output.to_dict())

    def test_closes_without_grade_when_an_insufficiency_rule_is_met(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.return_value = decisions(
            None, 75, 50, cuts_sufficient=False
        )

        assert harness.run_official() == 'evaluated'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        assert evaluation.score is None
        assert evaluation.effect_applied_at is None
        (part,) = evaluation.parts
        assert isinstance(part, PracticalPreparationResult)
        assert part.unassessable_record_keys == ('cuts',)
        assert harness.seeded.concept_observation_values() == [None]

    def test_a_closed_attempt_lets_the_learner_submit_again(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.return_value = decisions(
            None, 75, 50, cuts_sufficient=False
        )
        harness.run_official()

        with harness.seeded.database.transaction() as repositories:
            unresolved = repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                harness.seeded.attempt.skill_experience_id
            )

        assert unresolved is None

    def test_fails_recoverably_when_the_assessor_is_unavailable(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.side_effect = ServiceUnavailableError

        assert harness.run_official() == 'failed'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.FAILED
        assert evaluation.parts == ()
        assert evaluation.score is None

    def test_logs_only_the_stage_and_error_class_of_a_failure(
        self, harness: Harness, caplog: pytest.LogCaptureFixture
    ) -> None:
        harness.assessor.assess.side_effect = ServiceUnavailableError(
            'secret provider detail'
        )

        harness.run_official()

        messages = [record.getMessage() for record in caplog.records]
        failure = next(item for item in messages if 'evaluation failed' in item)
        assert 'stage=assess' in failure
        assert 'error_class=ServiceUnavailableError' in failure
        assert 'failure_code=evaluation_failed' in failure
        flattened = ' '.join(messages)
        assert 'secret provider detail' not in flattened
        assert 'fake-png' not in flattened
        assert harness.seeded.attempt.id not in flattened

    def test_fails_recoverably_when_the_assessor_answer_is_invalid(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.return_value = PracticePhotoDecisions(
            criteria=(criterion(CUT, 100),),
            records=decisions(100, 100, 100).records,
        )

        assert harness.run_official() == 'failed'

        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.FAILED
        )

    def test_closes_without_grade_for_the_real_model_output_on_a_dish_photo(
        self, harness: Harness
    ) -> None:
        # What the real model returned when the "during" photo showed a finished dish.
        harness.assessor.assess.return_value = PracticePhotoDecisions(
            criteria=decisions(50, None, 75).criteria,
            records=(
                PracticeRecordDecision(record_key='cuts', sufficient=True),
                PracticeRecordDecision(record_key='during', sufficient=False),
                PracticeRecordDecision(record_key='final', sufficient=True),
            ),
        )

        assert harness.run_official() == 'evaluated'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        (part,) = evaluation.parts
        assert isinstance(part, PracticalPreparationResult)
        assert part.unassessable_record_keys == ('during',)

    def test_fails_recoverably_for_uncertainty_that_does_not_prove_insufficiency(
        self, harness: Harness, caplog: pytest.LogCaptureFixture
    ) -> None:
        # The criterion is inconclusive but the record is reported sufficient, so no
        # insufficiency rule is satisfied.
        harness.assessor.assess.return_value = decisions(100, None, 100)

        assert harness.run_official() == 'failed'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.FAILED
        assert evaluation.status is not ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        failure = next(
            record.getMessage()
            for record in caplog.records
            if 'evaluation failed' in record.getMessage()
        )
        assert 'stage=apply' in failure
        assert 'error_class=EvaluationUnavailableError' in failure

    def test_fails_recoverably_when_a_photo_cannot_be_read(
        self, harness: Harness
    ) -> None:
        harness.storage.objects.clear()

        assert harness.run_official() == 'failed'

        harness.assessor.assess.assert_not_called()
        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.FAILED
        )

    def test_retry_reevaluates_the_same_attempt_without_a_new_submission(
        self, harness: Harness
    ) -> None:
        harness.assessor.assess.side_effect = ServiceUnavailableError
        harness.run_official()
        failed_run_id = harness.seeded.run_id
        retry = RetryChoiceEvaluationUseCase(
            harness.seeded.database,
            SystemClockProvider(),
            SystemIdentifierProvider(),
        )
        with harness.seeded.database.transaction() as repositories:
            experience = repositories.skill_experiences.find_by_id(
                harness.seeded.attempt.skill_experience_id
            )
            assert experience is not None
            goal_id = experience.goal_id
            skill_id = experience.skill_id
            account_id = (repositories.goals.find_by_id(goal_id) or Mock()).account_id
        retry.execute(
            account_id,
            goal_id,
            skill_id,
            harness.seeded.attempt.competency_id,
            harness.seeded.attempt.activity_id,
            harness.seeded.attempt.id,
        )
        renewed = harness.seeded.current_evaluation()
        assert renewed.status is ActivityEvaluationStatus.PENDING
        assert renewed.run_id is not None
        assert renewed.run_id != failed_run_id
        harness.assessor.assess.side_effect = None
        harness.assessor.assess.return_value = decisions(100, 100, 100)

        assert harness.run_official(run_id=renewed.run_id) == 'evaluated'

        evaluation = harness.seeded.current_evaluation()
        assert evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert evaluation.score == Decimal(100)
        assert evaluation.attempt_id == harness.seeded.attempt.id

    def test_reports_a_stale_run_without_calling_the_assessor(
        self, harness: Harness
    ) -> None:
        assert harness.run_official(run_id='01J00000000000000000000000') == 'stale'

        harness.assessor.assess.assert_not_called()
        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.PENDING
        )

    def test_a_duplicate_run_after_completion_is_a_no_op(
        self, harness: Harness
    ) -> None:
        assert harness.run_official() == 'evaluated'
        harness.assessor.assess.reset_mock()

        assert harness.run_official() == 'stale'

        harness.assessor.assess.assert_not_called()
        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.COMPLETED
        )

    def test_a_late_run_does_not_recreate_data_after_the_experience_was_removed(
        self, harness: Harness
    ) -> None:
        with harness.seeded.database.transaction() as repositories:
            experience = repositories.skill_experiences.find_by_id(
                harness.seeded.attempt.skill_experience_id
            )
            assert experience is not None
            repositories.skill_experiences.remove(experience)

        assert harness.run_official() == 'stale'

        harness.assessor.assess.assert_not_called()
        with harness.seeded.database.transaction() as repositories:
            assert (
                repositories.activity_attempts.find_by_id(harness.seeded.attempt.id)
                is None
            )
            assert (
                repositories.concept_observations.find_many_by_attempt_id(
                    harness.seeded.attempt.id
                )
                == []
            )

    def test_ignores_an_input_that_is_not_an_official_run(
        self, harness: Harness
    ) -> None:
        harness.workflow.run(json.dumps({'handoff_ref': 'x' * 30}))

        harness.assessor.assess.assert_not_called()
        assert (
            harness.seeded.current_evaluation().status
            is ActivityEvaluationStatus.PENDING
        )

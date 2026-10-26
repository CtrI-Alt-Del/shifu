from unittest.mock import create_autospec
import pytest
from shifu.intelligence.core.domain.enums import (
    PlanningIntentKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.structures import PlanningOperationResult
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import CompletePlanningOperationUseCase
from shifu.shared.core.interfaces import ClockProvider
from tests.intelligence.core.use_cases.planning_test_setup import (
    NEXT_OPERATION_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
    batch,
    started_session,
)
from shifu.intelligence.core.domain.structures.planning_operation_result import (
    VALIDATION_EXHAUSTED_CODE,
)
from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NOW,
    BOUNDARY_OPERATION_ID,
    BOUNDARY_NEXT_OPERATION_ID,
    boundary_batch,
    boundary_proposal,
    boundary_session,
    boundary_complete,
)


class TestCompletePlanningOperationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = CompletePlanningOperationUseCase(self.sessions, self.clock)
        self.result = PlanningOperationResult.for_batch(
            batch(), classification=PlanningIntentKind.AMBIGUOUS
        )

    def test_should_apply_the_result_of_the_current_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        applied = self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result)

        assert applied is True
        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.batch is not None
        assert session.classification is PlanningIntentKind.AMBIGUOUS
        assert session.consulted_curriculum is True
        assert session.operation is None
        self.sessions.update.assert_called_once_with(session)

    def test_should_drop_a_result_for_a_planning_that_was_cancelled(self) -> None:
        self.sessions.find_by_id.return_value = None

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result) is False
        self.sessions.update.assert_not_called()

    def test_should_drop_a_result_of_a_superseded_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        assert (
            self.use_case.execute(PLANNING_ID, NEXT_OPERATION_ID, 1, self.result)
            is False
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        self.sessions.update.assert_not_called()

    def test_should_drop_a_result_that_loses_the_concurrent_write(self) -> None:
        self.sessions.find_by_id.return_value = started_session()
        self.sessions.update.return_value = False

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1, self.result) is False


class TestCompletePlanningOperationMigratedTransitions:
    @pytest.mark.parametrize(
        ('operation_id', 'generation'),
        [(BOUNDARY_NEXT_OPERATION_ID, 1), (BOUNDARY_OPERATION_ID, 2)],
    )
    def test_should_discard_results_that_miss_the_operation_or_generation_fence(
        self, operation_id: str, generation: int
    ) -> None:
        session = boundary_session()
        assert not boundary_complete(
            session,
            operation_id,
            generation,
            PlanningOperationResult.for_batch(boundary_batch()),
            BOUNDARY_NOW,
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None

    def test_should_discard_a_second_result_for_the_same_operation(self) -> None:
        session = boundary_session()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(boundary_batch()),
            BOUNDARY_NOW,
        )
        assert not boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(boundary_proposal()),
            BOUNDARY_NOW,
        )
        assert session.status is PlanningSessionStatus.INTERVIEW

    @pytest.mark.parametrize(
        ('result', 'status', 'failure_code'),
        [
            (
                PlanningOperationResult.out_of_scope(
                    classification=PlanningIntentKind.OUT_OF_SCOPE
                ),
                PlanningSessionStatus.OUT_OF_SCOPE,
                None,
            ),
            (
                PlanningOperationResult.unsupported(),
                PlanningSessionStatus.UNSUPPORTED,
                None,
            ),
            (
                PlanningOperationResult.validation_failed(),
                PlanningSessionStatus.VALIDATION_FAILED,
                VALIDATION_EXHAUSTED_CODE,
            ),
            (
                PlanningOperationResult.failed(),
                PlanningSessionStatus.FAILED,
                'service_unavailable',
            ),
        ],
    )
    def test_should_expose_distinguishable_outcomes_with_a_learner_message(
        self,
        result: PlanningOperationResult,
        status: PlanningSessionStatus,
        failure_code: str | None,
    ) -> None:
        session = boundary_session()
        assert boundary_complete(
            session, BOUNDARY_OPERATION_ID, 1, result, BOUNDARY_NOW
        )
        assert session.status is status
        assert session.message
        assert session.failure_code == failure_code
        assert session.operation is None
        assert session.batch is None
        assert session.proposal is None

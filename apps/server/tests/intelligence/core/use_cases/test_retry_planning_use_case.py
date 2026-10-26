from unittest.mock import create_autospec
import pytest
from shifu.intelligence.core.domain.enums import (
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import RetryPlanningUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NEXT_OPERATION_ID,
    NOW,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    failed_session,
    interviewing_session,
)
from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningOperationResult,
)
from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NOW,
    BOUNDARY_NEXT_OPERATION_ID,
    boundary_interviewing,
    boundary_complete,
    boundary_answer,
    boundary_retry,
)


class TestRetryPlanningUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = NEXT_OPERATION_ID
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = RetryPlanningUseCase(
            self.sessions, self.database, self.identifiers, self.clock
        )

    def test_should_rerun_a_failed_planning_over_the_preserved_context(self) -> None:
        session = failed_session()
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result.status is PlanningSessionStatus.PROCESSING
        assert result.operation is not None
        assert result.operation.kind is PlanningOperationKind.RETRY
        assert result.intent == 'Quero aprender web'
        assert result.failure_code is None
        self.sessions.update.assert_called_once_with(session)
        self.repositories.events.add.assert_called_once_with(
            PlanningOperationRequestedEvent(
                payload=PlanningOperationRequestedPayload(
                    planning_id=PLANNING_ID,
                    operation_id=NEXT_OPERATION_ID,
                    generation=1,
                )
            )
        )

    def test_should_refuse_a_retry_without_a_failure(self) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()

        with pytest.raises(PlanningStateConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_the_retry_that_loses_the_concurrent_write(self) -> None:
        self.sessions.find_by_id.return_value = failed_session()
        self.sessions.update.return_value = False

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.database.transaction.assert_not_called()

    def test_should_hide_a_foreign_planning(self) -> None:
        self.sessions.find_by_id.return_value = failed_session(OTHER_ACCOUNT_ID)

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()


class TestRetryPlanningMigratedTransitions:
    @pytest.mark.parametrize(
        'result',
        [PlanningOperationResult.failed(), PlanningOperationResult.validation_failed()],
    )
    def test_should_retry_only_after_a_failure_and_keep_the_context(
        self, result: PlanningOperationResult
    ) -> None:
        session = boundary_interviewing()
        boundary_answer(
            session,
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            BOUNDARY_NEXT_OPERATION_ID,
            BOUNDARY_NOW,
        )
        assert boundary_complete(
            session, BOUNDARY_NEXT_OPERATION_ID, 1, result, BOUNDARY_NOW
        )
        assert session.message is not None
        assert session.failure_code is not None
        boundary_retry(session, 'op-3', BOUNDARY_NOW)
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.RETRY
        assert session.answered_batch_count == 1
        assert session.message is None
        assert session.failure_code is None

    def test_should_refuse_a_retry_without_a_failure(self) -> None:
        session = boundary_interviewing()
        with pytest.raises(PlanningStateConflictError):
            boundary_retry(session, BOUNDARY_NEXT_OPERATION_ID, BOUNDARY_NOW)

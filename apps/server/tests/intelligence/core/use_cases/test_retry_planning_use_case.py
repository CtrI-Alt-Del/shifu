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

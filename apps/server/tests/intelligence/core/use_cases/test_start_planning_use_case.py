from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import PlanningStateConflictError
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import StartPlanningUseCase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCESS_REVISION,
    ACCOUNT_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
)


class TestStartPlanningUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.access.authorize.return_value = MentorAccessGrant(
            account_id=ACCOUNT_ID,
            access_revision=ACCESS_REVISION,
            operation_key=PLANNING_ID,
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.side_effect = [PLANNING_ID, OPERATION_ID]
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = StartPlanningUseCase(
            self.sessions, self.database, self.access, self.identifiers, self.clock
        )

    def test_should_store_a_processing_planning_and_request_its_first_operation(
        self,
    ) -> None:
        session = self.use_case.execute(ACCOUNT_ID, '  Quero aprender  web ')

        assert session.id == PLANNING_ID
        assert session.account_id == ACCOUNT_ID
        assert session.access_revision == ACCESS_REVISION
        assert session.intent == 'Quero aprender web'
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.generation == 1
        assert session.operation is not None
        assert session.operation.id == OPERATION_ID
        assert session.operation.kind is PlanningOperationKind.START
        assert session.created_at == NOW
        self.access.authorize.assert_called_once_with(ACCOUNT_ID, PLANNING_ID)
        self.sessions.add.assert_called_once_with(session)
        self.repositories.events.add.assert_called_once_with(
            PlanningOperationRequestedEvent(
                payload=PlanningOperationRequestedPayload(
                    planning_id=PLANNING_ID, operation_id=OPERATION_ID, generation=1
                )
            )
        )

    def test_should_not_request_an_operation_when_the_planning_cannot_be_stored(
        self,
    ) -> None:
        self.sessions.add.side_effect = PlanningStateConflictError

        with pytest.raises(PlanningStateConflictError):
            self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.database.transaction.assert_not_called()

    def test_should_not_store_anything_when_the_account_is_not_authorized(
        self,
    ) -> None:
        self.access.authorize.side_effect = AuthorizationError

        with pytest.raises(AuthorizationError):
            self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.sessions.add.assert_not_called()
        self.database.transaction.assert_not_called()

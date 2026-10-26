from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    PlanningIntentKind,
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    PlanningOperationResult,
    PlanningAnswer,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import RestartPlanningUseCase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NEXT_OPERATION_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
    proposal,
    interviewing_session,
    started_session,
)


class TestRestartPlanningUseCase:
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
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.access.authorize.return_value = MentorAccessGrant(
            account_id=ACCOUNT_ID,
            access_revision='revision-2',
            operation_key=PLANNING_ID,
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = NEXT_OPERATION_ID
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = RestartPlanningUseCase(
            self.sessions, self.database, self.access, self.identifiers, self.clock
        )

    def test_should_open_a_new_generation_with_the_submitted_intent(self) -> None:
        session = started_session()
        assert session.complete(
            OPERATION_ID, 1, PlanningOperationResult.for_proposal(proposal()), NOW
        )
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID, ' Agora  APIs ')

        assert result.generation == 2
        assert result.intent == 'Agora APIs'
        assert result.access_revision == 'revision-2'
        assert result.status is PlanningSessionStatus.PROCESSING
        assert result.operation is not None
        assert result.operation.kind is PlanningOperationKind.RESTART
        assert result.proposal is None
        self.access.authorize.assert_called_once_with(ACCOUNT_ID, PLANNING_ID)
        self.sessions.update.assert_called_once_with(session)
        self.repositories.events.add.assert_called_once_with(
            PlanningOperationRequestedEvent(
                payload=PlanningOperationRequestedPayload(
                    planning_id=PLANNING_ID,
                    operation_id=NEXT_OPERATION_ID,
                    generation=2,
                )
            )
        )

    def test_should_refuse_a_restart_while_an_operation_is_running(self) -> None:
        self.sessions.find_by_id.return_value = started_session()

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'Agora APIs')

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_the_restart_that_loses_the_concurrent_write(self) -> None:
        session = started_session()
        assert session.complete(OPERATION_ID, 1, PlanningOperationResult.failed(), NOW)
        self.sessions.find_by_id.return_value = session
        self.sessions.update.return_value = False

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'Agora APIs')

        self.database.transaction.assert_not_called()

    def test_should_hide_a_missing_planning(self) -> None:
        self.sessions.find_by_id.return_value = None

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'Agora APIs')

        self.access.authorize.assert_not_called()

    def test_should_discard_prior_answers_classification_and_catalog_context(
        self,
    ) -> None:
        session = interviewing_session()
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            NEXT_OPERATION_ID,
            NOW,
        )
        assert session.complete(
            NEXT_OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(
                proposal(), classification=PlanningIntentKind.LEARNING
            ),
            NOW,
        )
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID, '  Agora quero APIs ')

        assert result.generation == 2
        assert result.intent == 'Agora quero APIs'
        assert result.access_revision == 'revision-2'
        assert result.answered_batches == ()
        assert result.proposal is None
        assert result.classification is None
        assert result.consulted_curriculum is False
        self.sessions.update.assert_called_once_with(result)

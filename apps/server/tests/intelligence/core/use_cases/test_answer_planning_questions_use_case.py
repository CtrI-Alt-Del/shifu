from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningAnswersInvalidError,
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import PlanningAnswer
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import AnswerPlanningQuestionsUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NEXT_OPERATION_ID,
    NOW,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
)

_VALID = (PlanningAnswer(question_id='q1', option_ids=('o2',)),)


class TestAnswerPlanningQuestionsUseCase:
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
        self.use_case = AnswerPlanningQuestionsUseCase(
            self.sessions, self.database, self.identifiers, self.clock
        )

    def test_should_record_the_batch_and_request_the_next_operation(self) -> None:
        session = interviewing_session()
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        assert result is session
        assert result.status is PlanningSessionStatus.PROCESSING
        assert result.operation is not None
        assert result.operation.id == NEXT_OPERATION_ID
        assert result.operation.kind is PlanningOperationKind.ANSWER
        assert result.batch is None
        assert result.answered_batch_count == 1
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

    @pytest.mark.parametrize(
        'answers',
        [
            (),
            (PlanningAnswer(question_id='q1', option_ids=('o9',)),),
            (PlanningAnswer(question_id='q1', option_ids=('nao-sei', 'o1')),),
        ],
    )
    def test_should_reject_invalid_answers_without_any_write(
        self, answers: tuple[PlanningAnswer, ...]
    ) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()

        with pytest.raises(PlanningAnswersInvalidError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', answers)

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_answers_while_an_operation_is_running(self) -> None:
        self.sessions.find_by_id.return_value = started_session()

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_the_submission_that_loses_the_concurrent_write(
        self,
    ) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()
        self.sessions.update.return_value = False

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        self.database.transaction.assert_not_called()

    def test_should_hide_a_foreign_planning(self) -> None:
        self.sessions.find_by_id.return_value = interviewing_session(OTHER_ACCOUNT_ID)

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        self.sessions.update.assert_not_called()

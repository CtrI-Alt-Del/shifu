from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningOperationResult,
)
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import PreparePlanningOperationUseCase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import MentorAccessProvider
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCESS_REVISION,
    ACCOUNT_ID,
    NEXT_OPERATION_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
)


class TestPreparePlanningOperationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.use_case = PreparePlanningOperationUseCase(self.sessions, self.access)

    def test_should_describe_the_current_operation_after_checking_the_access(
        self,
    ) -> None:
        session = interviewing_session()
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            NEXT_OPERATION_ID,
            NOW,
        )
        self.sessions.find_by_id.return_value = session

        context = self.use_case.execute(PLANNING_ID, NEXT_OPERATION_ID, 1)

        assert context is not None
        assert context.planning_id == PLANNING_ID
        assert context.operation_id == NEXT_OPERATION_ID
        assert context.generation == 1
        assert context.account_id == ACCOUNT_ID
        assert context.intent == 'Quero aprender web'
        assert context.answers == ('Sites',)
        assert context.classification is None
        self.access.assert_current.assert_called_once_with(
            MentorAccessGrant(
                account_id=ACCOUNT_ID,
                access_revision=ACCESS_REVISION,
                operation_key=PLANNING_ID,
            )
        )
        self.sessions.remove.assert_not_called()

    @pytest.mark.parametrize(
        ('operation_id', 'generation'),
        [(NEXT_OPERATION_ID, 1), (OPERATION_ID, 2)],
    )
    def test_should_return_nothing_for_a_superseded_operation(
        self, operation_id: str, generation: int
    ) -> None:
        self.sessions.find_by_id.return_value = started_session()

        assert self.use_case.execute(PLANNING_ID, operation_id, generation) is None
        self.access.assert_current.assert_not_called()

    def test_should_return_nothing_for_a_missing_or_idle_planning(self) -> None:
        idle = started_session()
        assert idle.complete(OPERATION_ID, 1, PlanningOperationResult.failed(), NOW)
        self.sessions.find_by_id.side_effect = [None, idle]

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1) is None
        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1) is None
        self.access.assert_current.assert_not_called()

    def test_should_purge_the_planning_when_the_account_access_is_stale(
        self,
    ) -> None:
        self.sessions.find_by_id.return_value = started_session()
        self.access.assert_current.side_effect = AuthorizationError

        assert self.use_case.execute(PLANNING_ID, OPERATION_ID, 1) is None
        self.sessions.remove.assert_called_once_with(PLANNING_ID)

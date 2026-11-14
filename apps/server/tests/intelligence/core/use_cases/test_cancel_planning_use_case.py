from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.errors import PlanningSessionNotFoundError
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import CancelPlanningUseCase
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    started_session,
)


class TestCancelPlanningUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.remove.return_value = True
        self.use_case = CancelPlanningUseCase(self.sessions)

    def test_should_remove_the_owner_planning_even_while_it_is_processing(
        self,
    ) -> None:
        self.sessions.find_by_id.return_value = started_session()

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.remove.assert_called_once_with(PLANNING_ID)

    def test_should_ignore_a_planning_that_no_longer_exists(self) -> None:
        self.sessions.find_by_id.return_value = None

        self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.remove.assert_not_called()

    def test_should_hide_a_foreign_planning_without_removing_it(self) -> None:
        self.sessions.find_by_id.return_value = started_session(OTHER_ACCOUNT_ID)

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.remove.assert_not_called()

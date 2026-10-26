from datetime import timedelta
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import PlanningSessionStatus
from shifu.intelligence.core.domain.errors import PlanningSessionNotFoundError
from shifu.intelligence.core.domain.structures.planning_operation_result import (
    FAILED_MESSAGE,
    OPERATION_TIMEOUT_CODE,
)
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import GetPlanningSessionUseCase
from shifu.shared.core.interfaces import ClockProvider

from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NOW,
    boundary_expire,
    boundary_session,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NOW,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
)


_TIMEOUT = timedelta(minutes=3)


class TestGetPlanningSessionUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW + timedelta(seconds=30)
        self.use_case = GetPlanningSessionUseCase(self.sessions, self.clock, _TIMEOUT)

    def test_should_return_the_owner_planning_without_writing(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result is session
        assert result.status is PlanningSessionStatus.PROCESSING
        self.sessions.find_by_id.assert_called_once_with(PLANNING_ID)
        self.sessions.update.assert_not_called()

    @pytest.mark.parametrize('stored', [None, 'other-account'])
    def test_should_hide_missing_and_foreign_plannings(
        self, stored: str | None
    ) -> None:
        self.sessions.find_by_id.return_value = (
            started_session(OTHER_ACCOUNT_ID) if stored else None
        )

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        self.sessions.update.assert_not_called()

    def test_should_report_a_timed_out_operation_as_a_recoverable_failure(
        self,
    ) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.clock.now.return_value = NOW + _TIMEOUT

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result.status is PlanningSessionStatus.FAILED
        assert result.failure_code == OPERATION_TIMEOUT_CODE
        assert result.operation is None
        assert result.intent == 'Quero aprender web'
        self.sessions.update.assert_called_once_with(session)

    def test_should_expose_the_newer_state_when_the_timeout_write_loses(
        self,
    ) -> None:
        stale = started_session()
        fresh = interviewing_session()
        self.sessions.find_by_id.side_effect = [stale, fresh]
        self.sessions.update.return_value = False
        self.clock.now.return_value = NOW + _TIMEOUT

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        assert result is fresh
        assert result.status is PlanningSessionStatus.INTERVIEW
        assert self.sessions.find_by_id.call_count == 2

    @pytest.mark.parametrize(
        'elapsed', [timedelta(minutes=2), timedelta(minutes=3), timedelta(hours=1)]
    )
    def test_should_expire_exactly_at_the_timeout_and_only_once(
        self, elapsed: timedelta
    ) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.clock.now.return_value = NOW + elapsed

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID)

        if elapsed < _TIMEOUT:
            assert result.status is PlanningSessionStatus.PROCESSING
            self.sessions.update.assert_not_called()
        else:
            assert result.status is PlanningSessionStatus.FAILED
            assert result.failure_code == OPERATION_TIMEOUT_CODE
            assert result.message
            assert result.operation is None
            self.sessions.update.assert_called_once_with(result)
            self.sessions.update.reset_mock()
            assert self.use_case.execute(ACCOUNT_ID, PLANNING_ID) is result
            self.sessions.update.assert_not_called()


class TestGetPlanningSessionMigratedTransitions:
    def test_should_expire_only_a_processing_operation_older_than_the_timeout(
        self,
    ) -> None:
        session = boundary_session()
        timeout = timedelta(minutes=3)
        assert not boundary_expire(
            session, BOUNDARY_NOW + timedelta(minutes=2), timeout
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        assert boundary_expire(session, BOUNDARY_NOW + timeout, timeout)
        assert session.status is PlanningSessionStatus.FAILED
        assert session.failure_code == OPERATION_TIMEOUT_CODE
        assert session.message == FAILED_MESSAGE
        assert session.operation is None
        assert not boundary_expire(session, BOUNDARY_NOW + timedelta(hours=1), timeout)

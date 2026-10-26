from datetime import timedelta
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    PlanningOperationStage,
    PlanningSessionStatus,
)
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import ReportPlanningProgressUseCase
from shifu.shared.core.interfaces import ClockProvider
from tests.intelligence.core.use_cases.planning_test_setup import (
    NEXT_OPERATION_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
)


class TestReportPlanningProgressUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = ReportPlanningProgressUseCase(self.sessions, self.clock)

    def test_should_store_the_stage_of_the_current_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        reported = self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 1, PlanningOperationStage.RETRIEVING
        )

        assert reported is True
        assert session.operation is not None
        assert session.operation.id == OPERATION_ID
        assert session.operation.stage is PlanningOperationStage.RETRIEVING
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.updated_at == NOW
        self.sessions.update.assert_called_once_with(session)

    def test_should_drop_progress_of_a_planning_that_was_cancelled(self) -> None:
        self.sessions.find_by_id.return_value = None

        assert (
            self.use_case.execute(
                PLANNING_ID, OPERATION_ID, 1, PlanningOperationStage.ANALYZING
            )
            is False
        )
        self.sessions.update.assert_not_called()

    def test_should_drop_progress_of_a_superseded_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        assert (
            self.use_case.execute(
                PLANNING_ID, NEXT_OPERATION_ID, 1, PlanningOperationStage.COMPOSING
            )
            is False
        )
        assert session.operation is not None
        assert session.operation.stage is None
        self.sessions.update.assert_not_called()

    def test_should_drop_progress_once_the_operation_finished(self) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()

        assert (
            self.use_case.execute(
                PLANNING_ID, OPERATION_ID, 1, PlanningOperationStage.INTERVIEWING
            )
            is False
        )
        self.sessions.update.assert_not_called()

    def test_should_report_a_lost_concurrent_write(self) -> None:
        self.sessions.find_by_id.return_value = started_session()
        self.sessions.update.return_value = False

        assert (
            self.use_case.execute(
                PLANNING_ID, OPERATION_ID, 1, PlanningOperationStage.ANALYZING
            )
            is False
        )

    def test_should_replace_the_stage_without_restarting_the_operation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session
        self.clock.now.return_value = NOW + timedelta(seconds=5)
        assert self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 1, PlanningOperationStage.ANALYZING
        )

        assert self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 1, PlanningOperationStage.COMPOSING
        )

        assert session.operation is not None
        assert session.operation.stage is PlanningOperationStage.COMPOSING
        assert session.operation.started_at == NOW
        assert session.updated_at == NOW + timedelta(seconds=5)

    def test_should_discard_progress_from_a_stale_generation(self) -> None:
        session = started_session()
        self.sessions.find_by_id.return_value = session

        assert not self.use_case.execute(
            PLANNING_ID, OPERATION_ID, 2, PlanningOperationStage.RETRIEVING
        )

        assert session.operation is not None
        assert session.operation.stage is None
        assert session.updated_at == NOW
        self.sessions.update.assert_not_called()

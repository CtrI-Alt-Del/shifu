from datetime import timedelta
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.enums import (
    PlanningOperationStage,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.structures import PlanningOperationResult
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import ReportPlanningProgressUseCase
from shifu.shared.core.interfaces import ClockProvider

from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NEXT_OPERATION_ID,
    BOUNDARY_NOW,
    BOUNDARY_OPERATION_ID,
    BOUNDARY_PLANNING_ID,
    boundary_batch,
    boundary_complete,
    boundary_progress,
    boundary_proposal,
    boundary_start,
)
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


class TestReportPlanningProgressMigratedTransitions:
    def _started(self) -> PlanningSession:
        return boundary_start(
            BOUNDARY_PLANNING_ID,
            '01JACCOUNT000000000000TEST',
            'revision-1',
            'Quero aprender web',
            BOUNDARY_OPERATION_ID,
            BOUNDARY_NOW,
        )

    def test_should_record_the_stage_of_the_current_operation(self) -> None:
        session = self._started()
        later = BOUNDARY_NOW + timedelta(seconds=5)
        accepted = boundary_progress(
            session, BOUNDARY_OPERATION_ID, 1, PlanningOperationStage.RETRIEVING, later
        )
        assert accepted is True
        assert session.operation is not None
        assert session.operation.stage is PlanningOperationStage.RETRIEVING
        assert session.operation.id == BOUNDARY_OPERATION_ID
        assert session.operation.started_at == BOUNDARY_NOW
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.updated_at == later

    def test_should_replace_an_earlier_stage_with_the_latest_one(self) -> None:
        session = self._started()
        assert boundary_progress(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationStage.ANALYZING,
            BOUNDARY_NOW,
        )
        assert boundary_progress(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationStage.COMPOSING,
            BOUNDARY_NOW,
        )
        assert session.operation is not None
        assert session.operation.stage is PlanningOperationStage.COMPOSING

    def test_should_ignore_progress_of_another_operation_or_generation(self) -> None:
        session = self._started()
        assert (
            boundary_progress(
                session,
                BOUNDARY_NEXT_OPERATION_ID,
                1,
                PlanningOperationStage.ANALYZING,
                BOUNDARY_NOW,
            )
            is False
        )
        assert (
            boundary_progress(
                session,
                BOUNDARY_OPERATION_ID,
                2,
                PlanningOperationStage.ANALYZING,
                BOUNDARY_NOW,
            )
            is False
        )
        assert session.operation is not None
        assert session.operation.stage is None
        assert session.updated_at == BOUNDARY_NOW

    def test_should_ignore_progress_once_the_operation_completed(self) -> None:
        session = self._started()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(boundary_batch()),
            BOUNDARY_NOW,
        )
        assert (
            boundary_progress(
                session,
                BOUNDARY_OPERATION_ID,
                1,
                PlanningOperationStage.INTERVIEWING,
                BOUNDARY_NOW,
            )
            is False
        )
        assert session.operation is None
        assert session.status is PlanningSessionStatus.INTERVIEW

    def test_should_start_without_a_stage_and_clear_it_on_completion(self) -> None:
        session = self._started()
        assert session.operation is not None
        assert session.operation.stage is None
        assert boundary_progress(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationStage.COMPOSING,
            BOUNDARY_NOW,
        )
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(boundary_proposal()),
            BOUNDARY_NOW,
        )
        assert session.operation is None
        assert session.status is PlanningSessionStatus.PROPOSAL

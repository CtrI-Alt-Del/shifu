from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.errors import (
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.structures import PlanningOperationResult
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import ConfirmPlanningUseCase
from shifu.shared.core.domain.structures import (
    PlannedGoalConfirmation,
    PlannedGoalCreation,
    PlannedGoalSkill,
)
from shifu.shared.core.interfaces import PlannedGoalProvider
from tests.intelligence.core.use_cases.planning_test_setup import batch, proposal
from tests.intelligence.server.controllers.planning_test_support import (
    started_session,
)

if TYPE_CHECKING:
    from shifu.intelligence.core.domain.entities import PlanningSession

ACCOUNT_ID = '01JACCOUNT000000000000TEST'
CONFIRMATION_KEY = '3f0c2b9e-8d1a-4c57-9b2e-6a1d4f8c0e21'
NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)


def _proposed_session() -> PlanningSession:
    session = started_session(account_id=ACCOUNT_ID)
    operation = session.operation
    assert operation is not None
    assert session.complete(
        operation.id, 1, PlanningOperationResult.for_proposal(proposal()), NOW
    )
    return session


def _interviewing_session() -> PlanningSession:
    session = started_session(account_id=ACCOUNT_ID)
    operation = session.operation
    assert operation is not None
    assert session.complete(
        operation.id, 1, PlanningOperationResult.for_batch(batch()), NOW
    )
    return session


class _Setup:
    def __init__(self, session: PlanningSession | None) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.find_by_id.return_value = session
        self.planned_goals = create_autospec(PlannedGoalProvider, instance=True)
        self.planned_goals.create.return_value = PlannedGoalCreation(
            goal_id='goal-1', confirmation_key=CONFIRMATION_KEY, replayed=False
        )
        self.planned_goals.find.return_value = None
        self.subject = ConfirmPlanningUseCase(self.sessions, self.planned_goals)


class TestConfirmPlanningUseCase:
    def test_should_hand_the_stored_proposal_with_the_edits_and_end_the_planning(
        self,
    ) -> None:
        session = _proposed_session()
        setup = _Setup(session)

        creation = setup.subject.execute(
            ACCOUNT_ID,
            session.id,
            CONFIRMATION_KEY,
            'Título editado',
            'Descrição editada',
        )

        assert creation.goal_id == 'goal-1'
        handed = setup.planned_goals.create.call_args.args[0]
        assert isinstance(handed, PlannedGoalConfirmation)
        assert handed.account_id == ACCOUNT_ID
        assert handed.planning_id == session.id
        assert handed.confirmation_key == CONFIRMATION_KEY
        assert (handed.title, handed.description) == (
            'Título editado',
            'Descrição editada',
        )
        assert session.proposal is not None
        assert handed.skills == tuple(
            PlannedGoalSkill(
                skill_id=skill.skill_id, inclusion_reason=skill.justification
            )
            for skill in session.proposal.skills
        )
        setup.sessions.remove.assert_called_once_with(session.id)

    def test_should_recover_a_completed_confirmation_after_the_planning_is_gone(
        self,
    ) -> None:
        setup = _Setup(None)
        setup.planned_goals.find.return_value = PlannedGoalCreation(
            goal_id='goal-1', confirmation_key=CONFIRMATION_KEY, replayed=True
        )

        creation = setup.subject.execute(
            ACCOUNT_ID, '01ARZ3NDEKTSV4RRFFQ69G5FAV', CONFIRMATION_KEY, 'T', 'D'
        )

        assert creation.replayed is True
        setup.planned_goals.find.assert_called_once_with(ACCOUNT_ID, CONFIRMATION_KEY)
        setup.planned_goals.create.assert_not_called()

    def test_should_report_an_unknown_planning_without_a_stored_confirmation(
        self,
    ) -> None:
        setup = _Setup(None)

        with pytest.raises(PlanningSessionNotFoundError):
            setup.subject.execute(
                ACCOUNT_ID, '01ARZ3NDEKTSV4RRFFQ69G5FAV', CONFIRMATION_KEY, 'T', 'D'
            )

        setup.planned_goals.create.assert_not_called()

    def test_should_keep_another_accounts_planning_private(self) -> None:
        session = _proposed_session()
        setup = _Setup(session)

        with pytest.raises(PlanningSessionNotFoundError):
            setup.subject.execute(
                'someone-else', session.id, CONFIRMATION_KEY, 'T', 'D'
            )

        setup.planned_goals.create.assert_not_called()
        setup.sessions.remove.assert_not_called()

    def test_should_refuse_while_an_operation_runs(self) -> None:
        session = started_session(account_id=ACCOUNT_ID)
        setup = _Setup(session)

        with pytest.raises(PlanningOperationConflictError):
            setup.subject.execute(ACCOUNT_ID, session.id, CONFIRMATION_KEY, 'T', 'D')

        setup.planned_goals.create.assert_not_called()

    def test_should_refuse_a_planning_without_a_proposal(self) -> None:
        session = _interviewing_session()
        setup = _Setup(session)

        with pytest.raises(PlanningStateConflictError):
            setup.subject.execute(ACCOUNT_ID, session.id, CONFIRMATION_KEY, 'T', 'D')

        setup.planned_goals.create.assert_not_called()
        setup.sessions.remove.assert_not_called()

    def test_should_keep_the_planning_when_learning_refuses(self) -> None:
        session = _proposed_session()
        setup = _Setup(session)
        setup.planned_goals.create.side_effect = PlanningStateConflictError

        with pytest.raises(PlanningStateConflictError):
            setup.subject.execute(ACCOUNT_ID, session.id, CONFIRMATION_KEY, 'T', 'D')

        setup.sessions.remove.assert_not_called()

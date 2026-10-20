"""Helpers shared by the Planner controller tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.structures import PlanningOperationResult
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.intelligence.core.use_cases.planning_test_setup import batch, proposal
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import Engine

    from shifu.intelligence.core.interfaces import PlanningSessionsRepository
    from shifu.shared.core.interfaces import OutboxEvent

PLANNING_EVENT = 'intelligence/planning.operation.requested'
_IDENTIFIERS = SystemIdentifierProvider()


def sessions_of(client: TestClient) -> PlanningSessionsRepository:
    app = cast('FastAPI', client.app)
    return cast('PlanningSessionsRepository', app.state.planning_sessions_repository)


def planning_events(engine: Engine) -> list[OutboxEvent]:
    database = SqlalchemyIntelligenceDatabase(engine=engine)
    with database.transaction() as repositories:
        return [
            event
            for event in repositories.events.find_unrouted(
                now=datetime.now(UTC) + timedelta(seconds=5), limit=100
            )
            if event.name == PLANNING_EVENT
        ]


def started_session(
    *, account_id: str = MENTOR_ACCOUNT.account_id, started_at: datetime | None = None
) -> PlanningSession:
    return PlanningSession.start(
        _IDENTIFIERS.generate(),
        account_id,
        'controlled-test-revision',
        'Quero aprender web',
        _IDENTIFIERS.generate(),
        started_at or datetime.now(UTC),
    )


def interviewing_session(
    *, account_id: str = MENTOR_ACCOUNT.account_id
) -> PlanningSession:
    session = started_session(account_id=account_id)
    operation = session.operation
    assert operation is not None
    assert session.complete(
        operation.id,
        1,
        PlanningOperationResult.for_batch(batch()),
        datetime.now(UTC),
    )
    return session


def proposed_session(*, account_id: str = MENTOR_ACCOUNT.account_id) -> PlanningSession:
    session = started_session(account_id=account_id)
    operation = session.operation
    assert operation is not None
    assert session.complete(
        operation.id,
        1,
        PlanningOperationResult.for_proposal(proposal()),
        datetime.now(UTC),
    )
    return session


def failed_session(*, account_id: str = MENTOR_ACCOUNT.account_id) -> PlanningSession:
    session = started_session(account_id=account_id)
    operation = session.operation
    assert operation is not None
    assert session.complete(
        operation.id, 1, PlanningOperationResult.failed(), datetime.now(UTC)
    )
    return session

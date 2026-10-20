from __future__ import annotations

from typing import TYPE_CHECKING

from tests.intelligence.server.controllers.planning_test_support import (
    failed_session,
    interviewing_session,
    planning_events,
    sessions_of,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestRetryPlanningController:
    def test_should_rerun_a_failed_planning_over_its_preserved_context(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = failed_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/retry'
        )

        assert response.status_code == 202, response.text
        body = response.json()
        assert body['status'] == 'processing'
        assert body['operation']['kind'] == 'retry'
        assert body['intent'] == 'Quero aprender web'
        assert body['failure_code'] is None
        assert body['message'] is None
        events = planning_events(postgres_database.engine)
        assert len(events) == 1
        assert events[0].payload['planning_id'] == session.id

    def test_should_refuse_a_retry_without_a_failure(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = interviewing_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/retry'
        )

        assert response.status_code == 409
        assert response.json()['code'] == 'conflict'
        assert planning_events(postgres_database.engine) == []

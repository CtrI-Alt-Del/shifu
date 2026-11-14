from __future__ import annotations

from typing import TYPE_CHECKING

from tests.intelligence.server.controllers.planning_test_support import (
    planning_events,
    proposed_session,
    sessions_of,
    started_session,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestRestartPlanningController:
    def test_should_open_a_new_generation_and_discard_the_proposal(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = proposed_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/restart',
            json={'initial_intent': ' Agora quero  APIs '},
        )

        assert response.status_code == 202, response.text
        body = response.json()
        assert body['status'] == 'processing'
        assert body['generation'] == 2
        assert body['intent'] == 'Agora quero APIs'
        assert body['operation']['kind'] == 'restart'
        assert body['proposal'] is None
        assert body['answered_batch_count'] == 0
        events = planning_events(postgres_database.engine)
        assert len(events) == 1
        assert events[0].payload['generation'] == 2

    def test_should_refuse_a_restart_while_an_operation_runs(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session = started_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/restart',
            json={'initial_intent': 'Agora quero APIs'},
        )

        assert response.status_code == 409
        assert planning_events(postgres_database.engine) == []

    def test_should_reject_a_blank_intent(self, planning_client: TestClient) -> None:
        session = proposed_session()
        sessions_of(planning_client).add(session)

        response = planning_client.post(
            f'/intelligence/planning-sessions/{session.id}/restart',
            json={'initial_intent': ' '},
        )

        assert response.status_code == 422
        stored = sessions_of(planning_client).find_by_id(session.id)
        assert stored is not None
        assert stored.generation == 1

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.intelligence.server.controllers.planning_test_support import (
    sessions_of,
    started_session,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestCancelPlanningController:
    def test_should_delete_the_planning_even_while_it_is_processing(
        self, planning_client: TestClient
    ) -> None:
        session = started_session()
        sessions_of(planning_client).add(session)

        response = planning_client.delete(
            f'/intelligence/planning-sessions/{session.id}'
        )
        again = planning_client.delete(f'/intelligence/planning-sessions/{session.id}')
        detail = planning_client.get(f'/intelligence/planning-sessions/{session.id}')

        assert response.status_code == 204
        assert response.headers['cache-control'] == 'private, no-store'
        assert again.status_code == 204
        assert detail.status_code == 404
        assert sessions_of(planning_client).find_by_id(session.id) is None

    def test_should_keep_a_foreign_planning(self, planning_client: TestClient) -> None:
        session = started_session(account_id='01JACCOUNT00000000000OTHER')
        sessions_of(planning_client).add(session)

        response = planning_client.delete(
            f'/intelligence/planning-sessions/{session.id}'
        )

        assert response.status_code == 404
        assert sessions_of(planning_client).find_by_id(session.id) is not None

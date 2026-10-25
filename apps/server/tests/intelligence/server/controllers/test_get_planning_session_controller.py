from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from shifu.intelligence.core.domain.enums import (
    PlanningOperationStage,
    PlanningSessionStatus,
)
from tests.intelligence.server.controllers.planning_test_support import (
    failed_session,
    interviewing_session,
    proposed_session,
    sessions_of,
    started_session,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestGetPlanningSessionController:
    def test_should_expose_the_current_batch_while_interviewing(
        self, planning_client: TestClient
    ) -> None:
        session = interviewing_session()
        sessions_of(planning_client).add(session)

        response = planning_client.get(f'/intelligence/planning-sessions/{session.id}')

        assert response.status_code == 200, response.text
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert body['status'] == 'interview'
        assert body['operation'] is None
        assert body['batch']['id'] == 'batch-1'
        question = body['batch']['questions'][0]
        assert question['kind'] == 'single'
        assert question['options'] == [
            {'id': 'o1', 'text': 'Sites', 'exclusive': False, 'open': False},
            {'id': 'o2', 'text': 'APIs', 'exclusive': False, 'open': False},
            {'id': 'nao-sei', 'text': 'Não sei', 'exclusive': True, 'open': False},
        ]
        assert body['proposal'] is None

    def test_should_expose_a_validated_proposal_with_its_relations(
        self, planning_client: TestClient
    ) -> None:
        session = proposed_session()
        sessions_of(planning_client).add(session)

        response = planning_client.get(f'/intelligence/planning-sessions/{session.id}')

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['status'] == 'proposal'
        assert body['proposal'] == {
            'title': 'Aprender web',
            'description': 'Do HTML ao React.',
            'skills': [
                {
                    'skill_id': 'skill-html',
                    'name': 'HTML e CSS',
                    'justification': 'Base.',
                }
            ],
            'relations': [],
        }
        assert body['batch'] is None

    def test_should_report_a_timed_out_operation_as_a_recoverable_failure(
        self, planning_client: TestClient
    ) -> None:
        session = started_session(started_at=datetime.now(UTC) - timedelta(minutes=10))
        sessions_of(planning_client).add(session)

        response = planning_client.get(f'/intelligence/planning-sessions/{session.id}')

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['status'] == 'failed'
        assert body['failure_code'] == 'operation_timeout'
        assert body['operation'] is None
        assert body['message']
        stored = sessions_of(planning_client).find_by_id(session.id)
        assert stored is not None
        assert stored.status is PlanningSessionStatus.FAILED

    def test_should_hide_foreign_unknown_and_malformed_plannings(
        self, planning_client: TestClient
    ) -> None:
        foreign = failed_session(account_id='01JACCOUNT00000000000OTHER')
        sessions_of(planning_client).add(foreign)

        hidden = planning_client.get(f'/intelligence/planning-sessions/{foreign.id}')
        unknown = planning_client.get(
            '/intelligence/planning-sessions/01ARZ3NDEKTSV4RRFFQ69G5FAV'
        )
        malformed = planning_client.get('/intelligence/planning-sessions/not-a-ulid')

        assert hidden.status_code == 404
        assert hidden.json()['code'] == 'not_found'
        assert unknown.status_code == 404
        assert malformed.status_code == 422
        assert sessions_of(planning_client).find_by_id(foreign.id) is not None

    def test_should_expose_the_stage_reported_by_the_running_operation(
        self, planning_client: TestClient
    ) -> None:
        session = started_session()
        sessions_of(planning_client).add(session)

        before = planning_client.get(f'/intelligence/planning-sessions/{session.id}')
        operation = session.operation
        assert operation is not None
        assert session.report_progress(
            operation.id, 1, PlanningOperationStage.RETRIEVING, datetime.now(UTC)
        )
        assert sessions_of(planning_client).update(session)
        after = planning_client.get(f'/intelligence/planning-sessions/{session.id}')

        assert before.status_code == 200, before.text
        assert before.json()['status'] == 'processing'
        assert before.json()['operation']['kind'] == 'start'
        assert before.json()['operation']['stage'] is None
        assert after.status_code == 200, after.text
        assert after.json()['operation']['stage'] == 'retrieving'
        assert after.json()['status'] == 'processing'

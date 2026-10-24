from __future__ import annotations

from typing import TYPE_CHECKING

from shifu.shared.settings import get_settings
from tests.fixtures.intelligence_fixture import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.planning_test_support import (
    PLANNING_EVENT,
    planning_events,
    sessions_of,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.postgres_fixture import PostgresDatabase
    from tests.fixtures.redis_fixture import RedisFixture


class TestStartPlanningController:
    def test_should_create_a_processing_planning_and_request_its_first_operation(
        self,
        planning_client: TestClient,
        postgres_database: PostgresDatabase,
        redis_fixture: RedisFixture,
    ) -> None:
        response = planning_client.post(
            '/intelligence/planning-sessions',
            json={'initial_intent': '  Quero aprender   a fazer sites  '},
        )

        assert response.status_code == 201, response.text
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert body['status'] == 'processing'
        assert body['intent'] == 'Quero aprender a fazer sites'
        assert body['generation'] == 1
        assert body['operation']['kind'] == 'start'
        assert body['batch'] is None
        assert body['proposal'] is None
        assert body['answered_batch_count'] == 0
        assert body['consulted_curriculum'] is False
        assert body['message'] is None
        assert set(body) == {
            'id',
            'status',
            'intent',
            'generation',
            'created_at',
            'updated_at',
            'operation',
            'consulted_curriculum',
            'batch',
            'answered_batch_count',
            'proposal',
            'message',
            'failure_code',
        }
        stored = sessions_of(planning_client).find_by_id(body['id'])
        assert stored is not None
        assert stored.account_id == MENTOR_ACCOUNT.account_id
        ttl = redis_fixture.client.ttl(f'shifu:planning:{body["id"]}')  # pyright: ignore[reportUnknownMemberType]
        assert 0 < int(ttl) <= get_settings().planning_session_ttl_seconds  # pyright: ignore[reportArgumentType]
        events = planning_events(postgres_database.engine)
        assert len(events) == 1
        assert events[0].name == PLANNING_EVENT
        payload = dict(events[0].payload)
        assert payload['planning_id'] == body['id']
        assert payload['generation'] == 1
        assert isinstance(payload['operation_id'], str)
        assert len(payload['operation_id']) == 26

    def test_should_reject_a_blank_intent_without_side_effects(
        self, planning_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        response = planning_client.post(
            '/intelligence/planning-sessions', json={'initial_intent': '   '}
        )

        assert response.status_code == 422
        assert response.json()['code'] == 'validation_error'
        assert planning_events(postgres_database.engine) == []

    def test_should_require_an_authenticated_learner(self, client: TestClient) -> None:
        response = client.post(
            '/intelligence/planning-sessions',
            json={'initial_intent': 'Quero aprender web'},
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

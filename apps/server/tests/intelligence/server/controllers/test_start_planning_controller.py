from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.shared.settings import get_settings
from tests.fixtures.intelligence_fixture import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.ai_quota_test_support import (
    EXHAUSTED_BODY,
    count_state,
    read_charge,
    read_month,
    seed_month,
)
from tests.intelligence.server.controllers.planning_test_support import (
    PLANNING_EVENT,
    planning_events,
    sessions_of,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx2 import Response

    from tests.fixtures.intelligence_fixture import IntelligenceFixture
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


class TestStartPlanningAiQuota:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        intelligence_fixture: IntelligenceFixture,
        planning_client: TestClient,
        redis_fixture: RedisFixture,
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = planning_client
        self.redis = redis_fixture

    def _plannings_in_redis(self) -> list[object]:
        return list(self.redis.client.scan_iter('shifu:planning:*'))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]

    def _start(self) -> Response:
        return self.client.post(
            '/intelligence/planning-sessions',
            json={'initial_intent': 'Quero aprender a fazer sites'},
        )

    def test_should_admit_the_start_and_record_its_operation_in_the_month(self) -> None:
        response = self._start()

        assert response.status_code == 201, response.text
        stored = sessions_of(self.client).find_by_id(response.json()['id'])
        assert stored is not None
        assert stored.operation is not None
        charge = read_charge(
            self.fixture, AiQuotaRequestKind.PLANNING_OPERATION, stored.operation.id
        )
        assert charge is not None
        assert charge.account_id == MENTOR_ACCOUNT.account_id
        assert charge.charged_units == 0
        month = read_month(self.fixture)
        assert month is not None
        assert (month.used_units, month.limit_units) == (0, 1000)

    @pytest.mark.parametrize('used_units', [1000, 1300])
    def test_should_refuse_the_start_with_429_and_create_nothing(
        self, used_units: int
    ) -> None:
        seed_month(self.fixture, used_units)
        before = count_state(self.fixture.postgres.engine)

        response = self._start()

        assert response.status_code == 429, response.text
        assert response.json() == EXHAUSTED_BODY
        assert count_state(self.fixture.postgres.engine) == before
        assert planning_events(self.fixture.postgres.engine) == []
        assert self._plannings_in_redis() == []
        month = read_month(self.fixture)
        assert month is not None
        assert month.used_units == used_units

    def test_should_admit_the_start_just_below_the_limit(self) -> None:
        seed_month(self.fixture, 999)

        assert self._start().status_code == 201

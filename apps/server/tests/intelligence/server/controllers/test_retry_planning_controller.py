from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    PlanningSessionStatus,
)
from tests.intelligence.server.controllers.ai_quota_test_support import (
    EXHAUSTED_BODY,
    count_state,
    read_charge,
    seed_month,
)
from tests.intelligence.server.controllers.planning_test_support import (
    failed_session,
    interviewing_session,
    planning_events,
    sessions_of,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.intelligence_fixture import IntelligenceFixture
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


class TestRetryPlanningAiQuota:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, planning_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = planning_client
        self.session = failed_session()
        sessions_of(planning_client).add(self.session)
        self.path = f'/intelligence/planning-sessions/{self.session.id}/retry'

    def test_should_admit_the_retry_and_record_its_operation_in_the_month(self) -> None:
        response = self.client.post(self.path)

        assert response.status_code == 202, response.text
        stored = sessions_of(self.client).find_by_id(self.session.id)
        assert stored is not None
        assert stored.operation is not None
        charge = read_charge(
            self.fixture, AiQuotaRequestKind.PLANNING_OPERATION, stored.operation.id
        )
        assert charge is not None
        assert charge.charged_units == 0

    @pytest.mark.parametrize('used_units', [1000, 1300])
    def test_should_refuse_the_retry_with_429_and_keep_the_failure(
        self, used_units: int
    ) -> None:
        seed_month(self.fixture, used_units)
        before = count_state(self.fixture.postgres.engine)

        response = self.client.post(self.path)

        assert response.status_code == 429, response.text
        assert response.json() == EXHAUSTED_BODY
        assert count_state(self.fixture.postgres.engine) == before
        assert planning_events(self.fixture.postgres.engine) == []
        stored = sessions_of(self.client).find_by_id(self.session.id)
        assert stored is not None
        assert stored.status is PlanningSessionStatus.FAILED
        assert stored.operation is None

    def test_should_admit_the_retry_just_below_the_limit(self) -> None:
        seed_month(self.fixture, 999)

        assert self.client.post(self.path).status_code == 202

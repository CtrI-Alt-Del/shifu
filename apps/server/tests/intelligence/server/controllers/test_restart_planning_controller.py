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
    planning_events,
    proposed_session,
    sessions_of,
    started_session,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx2 import Response

    from tests.fixtures.intelligence_fixture import IntelligenceFixture
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


class TestRestartPlanningAiQuota:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, planning_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = planning_client
        self.session = proposed_session()
        sessions_of(planning_client).add(self.session)
        self.path = f'/intelligence/planning-sessions/{self.session.id}/restart'

    def _restart(self) -> Response:
        return self.client.post(self.path, json={'initial_intent': 'Agora quero APIs'})

    def test_should_admit_the_restart_and_record_its_operation_in_the_month(
        self,
    ) -> None:
        response = self._restart()

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
    def test_should_refuse_the_restart_with_429_and_keep_the_proposal(
        self, used_units: int
    ) -> None:
        seed_month(self.fixture, used_units)
        before = count_state(self.fixture.postgres.engine)

        response = self._restart()

        assert response.status_code == 429, response.text
        assert response.json() == EXHAUSTED_BODY
        assert count_state(self.fixture.postgres.engine) == before
        assert planning_events(self.fixture.postgres.engine) == []
        stored = sessions_of(self.client).find_by_id(self.session.id)
        assert stored is not None
        assert stored.generation == 1
        assert stored.status is PlanningSessionStatus.PROPOSAL
        assert stored.proposal is not None

    def test_should_admit_the_restart_just_below_the_limit(self) -> None:
        seed_month(self.fixture, 999)

        assert self._restart().status_code == 202

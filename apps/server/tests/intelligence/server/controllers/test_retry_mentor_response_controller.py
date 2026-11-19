from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from tests.intelligence.server.controllers.ai_quota_test_support import (
    EXHAUSTED_BODY,
    charge_attempt,
    count_state,
    fail_attempt,
    read_charge,
    read_month,
    seed_month,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx2 import Response

    from tests.fixtures.intelligence_fixture import IntelligenceFixture

RETRY_KEY = '8d2b7c4e-4a1f-4c3e-9b52-6f1d3a7e9c01'


class TestRetryMentorResponseController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        self.session_id, self.attempt_id, _ = intelligence_fixture.create_session(
            mentor_client
        )
        # The first answer spent 30 units (10 + 5 * 4) and then failed.
        intelligence_fixture.start_processing(self.attempt_id)
        charge_attempt(
            intelligence_fixture, self.attempt_id, input_tokens=10, output_tokens=5
        )
        fail_attempt(intelligence_fixture, self.attempt_id)
        self.path = (
            f'/intelligence/mentor-sessions/{self.session_id}'
            f'/responses/{self.attempt_id}/retry'
        )

    def _retry(self, key: str = RETRY_KEY) -> Response:
        return self.client.post(self.path, json={'submission_key': key})

    def test_should_have_given_the_failed_answer_back_to_the_month(self) -> None:
        charge = read_charge(
            self.fixture, AiQuotaRequestKind.MENTOR_RESPONSE, self.attempt_id
        )
        assert charge is not None
        assert charge.refunded is True
        month = read_month(self.fixture)
        assert month is not None
        assert month.used_units == 0

    def test_should_admit_the_retry_and_record_the_new_attempt(self) -> None:
        response = self._retry()

        assert response.status_code == 202, response.text
        retry_attempt = response.json()['attempt_id']
        assert retry_attempt != self.attempt_id
        charge = read_charge(
            self.fixture, AiQuotaRequestKind.MENTOR_RESPONSE, retry_attempt
        )
        assert charge is not None
        assert charge.charged_units == 0
        assert charge.refunded is False

    @pytest.mark.parametrize('used_units', [1000, 1300])
    def test_should_refuse_the_retry_with_429_and_create_nothing(
        self, used_units: int
    ) -> None:
        seed_month(self.fixture, used_units)
        before = count_state(self.fixture.postgres.engine)

        response = self._retry()

        assert response.status_code == 429, response.text
        assert response.json() == EXHAUSTED_BODY
        assert count_state(self.fixture.postgres.engine) == before
        detail = self.client.get(f'/intelligence/mentor-sessions/{self.session_id}')
        assert detail.json()['response']['attempt_id'] == self.attempt_id
        assert detail.json()['response']['status'] == 'failed'

    def test_should_admit_the_retry_just_below_the_limit(self) -> None:
        seed_month(self.fixture, 999)

        assert self._retry().status_code == 202

    def test_should_replay_an_accepted_retry_even_after_the_limit_is_reached(
        self,
    ) -> None:
        accepted = self._retry()
        assert accepted.status_code == 202
        seed_month(self.fixture, 1000)
        before = count_state(self.fixture.postgres.engine)

        replay = self._retry()

        assert replay.status_code == 200, replay.text
        assert count_state(self.fixture.postgres.engine) == before

    def test_should_require_an_authenticated_learner(self, client: TestClient) -> None:
        response = client.post(self.path, json={'submission_key': RETRY_KEY})

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

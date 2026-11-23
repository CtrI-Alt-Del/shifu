from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.intelligence.server.controllers.ai_quota_test_support import (
    charge_attempt,
    fail_attempt,
    seed_month,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.intelligence_fixture import IntelligenceFixture


class TestGetMentorSessionAiUsageController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        self.session_id, self.attempt_id, self.message_id = (
            intelligence_fixture.create_session(mentor_client)
        )
        self.path = f'/intelligence/mentor-sessions/{self.session_id}/ai-usage'

    def _mentor_message_id(self) -> str:
        detail = self.client.get(
            f'/intelligence/mentor-sessions/{self.session_id}'
        ).json()
        return next(
            item['id']
            for item in detail['messages']['items']
            if item['role'] == 'mentor'
        )

    def test_should_return_the_quota_share_of_a_completed_answer(self) -> None:
        self.fixture.start_processing(self.attempt_id)
        # 10 input + 8 output tokens weigh 10 + 32 = 42 of the 1000 test units.
        charge_attempt(self.fixture, self.attempt_id, input_tokens=10, output_tokens=8)
        self.fixture.complete_response(
            self.session_id, self.attempt_id, self.message_id, claimed=True
        )

        response = self.client.get(self.path)

        assert response.status_code == 200, response.text
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.json() == {
            'items': [
                {
                    'message_id': self._mentor_message_id(),
                    'attempt_id': self.attempt_id,
                    'percentage': 4.2,
                }
            ]
        }

    def test_should_return_nothing_while_the_answer_is_still_running(self) -> None:
        self.fixture.start_processing(self.attempt_id)
        charge_attempt(self.fixture, self.attempt_id, input_tokens=10, output_tokens=8)

        response = self.client.get(self.path)

        assert response.status_code == 200, response.text
        assert response.json() == {'items': []}

    def test_should_leave_out_a_refunded_answer(self) -> None:
        self.fixture.start_processing(self.attempt_id)
        charge_attempt(self.fixture, self.attempt_id, input_tokens=10, output_tokens=8)
        fail_attempt(self.fixture, self.attempt_id)

        response = self.client.get(self.path)

        assert response.status_code == 200, response.text
        assert response.json() == {'items': []}

    def test_should_hide_a_session_of_another_account(self) -> None:
        seed_month(self.fixture, 0)

        with self.fixture.other_account_client() as other:
            response = other.get(self.path)

        assert response.status_code == 404, response.text

    def test_should_reject_a_malformed_session_id(self) -> None:
        response = self.client.get('/intelligence/mentor-sessions/not-a-ulid/ai-usage')

        assert response.status_code == 422, response.text

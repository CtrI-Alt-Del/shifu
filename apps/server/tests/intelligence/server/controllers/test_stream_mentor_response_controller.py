from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from typing import TYPE_CHECKING, Any

import pytest

from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.rest.controllers import stream_mentor_response_controller

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.fixtures.intelligence_fixture import IntelligenceFixture


def frames(body: str) -> list[tuple[int, dict[str, Any]]]:
    """The ``(id, data)`` of every event frame, skipping heartbeats."""
    parsed: list[tuple[int, dict[str, Any]]] = []
    for frame in body.split('\n\n'):
        fields = dict(
            line.split(':', 1)
            for line in frame.splitlines()
            if not line.startswith(':')
        )
        if 'data' in fields:
            parsed.append((int(fields['id']), json.loads(fields['data'])))
    return parsed


class TestStreamMentorResponseController:
    @pytest.fixture(autouse=True)
    def setup(
        self, intelligence_fixture: IntelligenceFixture, mentor_client: TestClient
    ) -> None:
        self.fixture = intelligence_fixture
        self.client = mentor_client
        self.session_id, self.attempt_id, self.message_id = (
            intelligence_fixture.create_session(mentor_client)
        )
        self.path = f'/intelligence/mentor-sessions/{self.session_id}/events'

    def test_should_stream_every_event_in_order_and_end_at_the_terminal_one(
        self,
    ) -> None:
        self.fixture.complete_response(
            self.session_id, self.attempt_id, self.message_id
        )

        response = self.client.get(self.path)

        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/event-stream')
        assert response.headers['cache-control'] == 'private, no-store'
        events = frames(response.text)
        sequences = [sequence for sequence, _ in events]
        assert sequences == sorted(sequences)
        assert len(sequences) >= 3
        assert events[0][1]['status'] == MentorResponseStatus.QUEUED.value
        assert events[-1][1]['status'] == MentorResponseStatus.COMPLETED.value
        assert all(data['attempt_id'] == self.attempt_id for _, data in events)

    def test_should_resume_after_the_last_event_id(self) -> None:
        self.fixture.complete_response(
            self.session_id, self.attempt_id, self.message_id
        )
        first = frames(self.client.get(self.path).text)

        response = self.client.get(
            self.path, headers={'Last-Event-ID': str(first[0][0])}
        )

        assert response.status_code == 200
        assert frames(response.text) == first[1:]

    def test_should_fail_an_orphaned_attempt_and_end_the_stream(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(stream_mentor_response_controller, '_POLL_SECONDS', 0.01)
        monkeypatch.setattr(
            stream_mentor_response_controller, '_RECOVERY_IDLE_POLLS', 1
        )
        self.fixture.start_processing(
            self.attempt_id, claimed_at=datetime.now(UTC) - timedelta(minutes=10)
        )

        response = self.client.get(self.path)

        assert response.status_code == 200
        last = frames(response.text)[-1][1]
        assert last['status'] == MentorResponseStatus.FAILED.value
        assert last['failure_code'] == 'service_unavailable'
        with self.fixture.database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id(self.attempt_id)
        assert attempt is not None
        assert attempt.status is MentorResponseStatus.FAILED

    def test_should_not_open_another_accounts_stream(self) -> None:
        with self.fixture.other_account_client() as other:
            response = other.get(self.path)

        assert response.status_code == 404

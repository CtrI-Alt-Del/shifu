from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import AuthenticationPipe
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe

if TYPE_CHECKING:
    from fastapi import Request

    from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput
    from sqlalchemy import Engine

    from tests.fixtures.postgres_fixture import PostgresDatabase


class _Provider:
    def __init__(self) -> None:
        self.events: list[TelemetryEventInput] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(event)


def _client(engine: Engine, provider: _Provider) -> TestClient:
    app = FastAPIApp.register(engine, telemetry_provider=provider)
    app.dependency_overrides[AuthenticationPipe.get_authenticated_user] = lambda: (
        AuthenticatedUser(
            account_id='account-secret',
            display_name='Pessoa Aprendente',
            time_zone=None,
        )
    )
    app.dependency_overrides[LearningPipe.get_curriculum_content_provider] = lambda: (
        object()
    )
    return TestClient(app)


@pytest.mark.parametrize('with_request_id', [True, False])
def test_create_goal_emits_success_telemetry_after_commit(
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
    with_request_id: bool,
) -> None:
    if not with_request_id:

        def no_request_id(_request: Request) -> None:
            return None

        monkeypatch.setattr(
            TelemetryPipe,
            'get_request_id',
            staticmethod(no_request_id),
        )
    provider = _Provider()
    request_id = '123e4567-e89b-42d3-a456-426614174000'
    with _client(postgres_database.engine, provider) as client:
        response = client.post(
            '/learning/goals',
            json={'title': 'Goal title', 'description': 'Goal description'},
            headers={'X-Request-ID': request_id},
        )

    assert response.status_code == 201
    event = next(
        event for event in provider.events if event['event'] == 'learning.goal.created'
    )
    assert event['level'] == 'INFO'
    assert event.get('operation') == 'goal.create'
    assert event.get('result') == 'success'
    assert event.get('request_id') == (request_id if with_request_id else None)
    assert 'account-secret' not in str(event)

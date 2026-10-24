from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from shifu.learning.pipes import LearningPipe
from shifu.learning.rest.controllers.remove_goal_controller import RemoveGoalController
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from shifu.shared.rest.middlewares.telemetry_middleware import TelemetryMiddleware


class _Provider:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)


def test_business_controller_emits_only_the_fixed_success_event() -> None:
    provider = _Provider()
    app = FastAPI()
    app.state.telemetry_provider = provider
    router = APIRouter(prefix='/learning')
    RemoveGoalController.handle(router)
    app.include_router(router)
    app.add_middleware(TelemetryMiddleware)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
        AuthenticatedUser(
            account_id='account-secret',
            display_name='Pessoa Aprendente',
            time_zone=None,
        )
    )
    app.dependency_overrides[LearningPipe.get_database] = lambda: object()

    with (
        patch(
            'shifu.learning.rest.controllers.remove_goal_controller.RemoveGoalUseCase'
        ) as remove_goal,
        TestClient(app) as client,
    ):
        response = client.delete(
            '/learning/goals/goal-secret',
            headers={'X-Request-ID': '123e4567-e89b-42d3-a456-426614174000'},
        )

    assert response.status_code == 204, response.text
    remove_goal.return_value.execute.assert_called_once_with(
        account_id='account-secret',
        goal_id='goal-secret',
    )
    event = next(
        event for event in provider.events if event['event'] == 'learning.goal.deleted'
    )
    assert event['level'] == 'INFO'
    assert event['operation'] == 'goal.delete'
    assert event['result'] == 'success'
    assert event['request_id'] == '123e4567-e89b-42d3-a456-426614174000'
    assert 'account-secret' not in str(event)
    assert 'goal-secret' not in str(event)

"""Persisted goal removal and safe business telemetry at the registered route."""

from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.fakers.identity.entities import AccountFaker
from shifu.fakers.learning.entities import GoalFaker
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.shared.telemetry_support import RecordingTelemetry

if TYPE_CHECKING:
    import pytest
    from fastapi import FastAPI
    from shifu.identity.core.interfaces import IdentityDatabase
    from shifu.learning.core.interfaces import LearningDatabase


class TestRemoveGoalController:
    def test_deletes_persisted_goal_and_emits_fixed_success_event(
        self, client: TestClient, monkeypatch: 'pytest.MonkeyPatch'
    ) -> None:
        app = cast('FastAPI', client.app)
        provider = RecordingTelemetry()
        app.state.telemetry_provider = provider
        account = AccountFaker.fake()
        goal = GoalFaker.fake(account_id=account.id)
        identity = cast('IdentityDatabase', app.state.identity_database)
        learning = cast('LearningDatabase', app.state.learning_database)
        with identity.transaction() as repos:
            repos.accounts.add(account)
        with learning.transaction() as repos:
            repos.goals.add(goal)
        user = AuthenticatedUser(
            account_id=account.id,
            display_name=account.display_name,
            time_zone=account.time_zone,
        )
        monkeypatch.setitem(
            app.dependency_overrides, SharedPipe.get_authenticated_user, lambda: user
        )
        request_id = '123e4567-e89b-42d3-a456-426614174000'

        response = client.delete(
            f'/learning/goals/{goal.id}', headers={'X-Request-ID': request_id}
        )

        assert response.status_code == 204, response.text
        assert response.content == b''
        with learning.transaction() as repos:
            assert repos.goals.find_by_id(goal.id) is None
        event = next(
            event
            for event in provider.events
            if event['event'] == 'learning.goal.deleted'
        )
        assert event['level'] == 'INFO'
        assert event.get('operation') == 'goal.delete'
        assert event.get('result') == 'success'
        assert event.get('request_id') == request_id
        assert account.id not in str(provider.events)
        assert goal.id not in str(provider.events)
        http_event = next(
            event
            for event in provider.events
            if event['event'] == 'http.request.completed'
        )
        assert http_event.get('route') == '/learning/goals/{goal_id}'

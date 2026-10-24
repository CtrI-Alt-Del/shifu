from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from fastapi import APIRouter, Response

import shifu.intelligence.rest.controllers.create_mentor_session_controller as create_session_module
import shifu.intelligence.rest.controllers.submit_mentor_message_controller as submit_message_module
from shifu.intelligence.rest.controllers.create_mentor_session_controller import (
    CreateMentorSessionController,
    Request as CreateSessionRequest,
)
from shifu.intelligence.rest.controllers.submit_mentor_message_controller import (
    Request as SubmitMessageRequest,
    SubmitMentorMessageController,
)

if TYPE_CHECKING:
    import pytest

_USER = SimpleNamespace(account_id='account')
_VALID_ULID = '01M00000000000000000000000'


def _endpoint(router: APIRouter, path: str, method: str) -> Any:
    route = cast(
        'Any',
        next(
            route
            for route in router.routes
            if getattr(route, 'path', None) == path
            and method in cast('Any', route).methods
        ),
    )
    return route.endpoint


def _validate_passthrough(value: Any, **_kwargs: Any) -> Any:
    return value


def test_create_session_route_calls_use_case_and_sets_replay_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = APIRouter()
    CreateMentorSessionController.handle(router)
    calls: list[tuple[object, ...]] = []

    class UseCase:
        def __init__(self, *_args: object) -> None:
            pass

        def execute(self, *args: object) -> SimpleNamespace:
            calls.append(args)
            return SimpleNamespace(created=False, detail={'session': 'detail'})

    monkeypatch.setattr(create_session_module, 'CreateMentorSessionUseCase', UseCase)
    monkeypatch.setattr(
        create_session_module,
        '_RESPONSE_ADAPTER',
        SimpleNamespace(validate_python=_validate_passthrough),
    )
    response = Response()
    endpoint = _endpoint(router, '/mentor-sessions', 'POST')
    result = endpoint(
        CreateSessionRequest(submission_key=uuid4(), first_message='hello'),
        response,
        _USER,
        object(),
        object(),
        object(),
        object(),
        object(),
    )

    assert result == {'session': 'detail'}
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'private, no-store'
    assert len(calls) == 1


def test_submit_message_route_calls_use_case_and_sets_response_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = APIRouter()
    SubmitMentorMessageController.handle(router)

    class UseCase:
        replayed = False

        def __init__(self, *_args: object) -> None:
            pass

        def execute(self, *_args: object) -> dict[str, str]:
            return {'session': 'detail'}

    monkeypatch.setattr(submit_message_module, 'SubmitMentorMessageUseCase', UseCase)
    monkeypatch.setattr(
        submit_message_module,
        '_RESPONSE_ADAPTER',
        SimpleNamespace(validate_python=_validate_passthrough),
    )
    response = Response()
    endpoint = _endpoint(router, '/mentor-sessions/{session_id}/messages', 'POST')
    result = endpoint(
        _VALID_ULID,
        SubmitMessageRequest(submission_key=uuid4(), content='hello'),
        response,
        _USER,
        object(),
        object(),
        object(),
        object(),
    )

    assert result == {'session': 'detail'}
    assert response.status_code == 202
    assert response.headers['cache-control'] == 'private, no-store'

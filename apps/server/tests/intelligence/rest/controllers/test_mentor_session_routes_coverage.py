from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import APIRouter, HTTPException, Response
from fastapi import Request as StarletteRequest
from fastapi import UploadFile

import shifu.intelligence.rest.controllers.create_mentor_session_controller as create_session_module
import shifu.intelligence.rest.controllers.submit_mentor_message_controller as submit_message_module
from shifu.intelligence.rest.controllers.create_mentor_session_controller import (
    CreateMentorSessionController,
    Request as CreateSessionRequest,
)
from shifu.intelligence.rest.controllers.mentor_attachments_controller import (
    CreateBatchRequest,
    MentorAttachmentsController,
)
from shifu.intelligence.rest.controllers.remove_mentor_session_controller import (
    RemoveMentorSessionController,
)
from shifu.intelligence.rest.controllers.submit_mentor_message_controller import (
    Request as SubmitMessageRequest,
    SubmitMentorMessageController,
)

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


def test_remove_session_route_rejects_a_malformed_id_directly() -> None:
    router = APIRouter()
    RemoveMentorSessionController.handle(router)
    endpoint = _endpoint(router, '/mentor-sessions/{session_id}', 'DELETE')

    with pytest.raises(HTTPException) as error:
        endpoint('not-a-ulid', Response(), _USER, object(), object(), object())

    assert error.value.status_code == 422


@pytest.mark.parametrize(
    ('path', 'method', 'args', 'expected_status'),
    [
        (
            '/mentor-attachment-batches',
            'POST',
            (
                CreateBatchRequest(session_id='invalid'),
                Response(),
                _USER,
                object(),
                object(),
                object(),
                object(),
            ),
            422,
        ),
        (
            '/mentor-attachment-batches/{batch_id}',
            'GET',
            ('invalid', Response(), _USER, object(), object(), object()),
            422,
        ),
        (
            '/mentor-attachment-batches/{batch_id}/attachments/{attachment_id}',
            'DELETE',
            ('invalid', _VALID_ULID, Response(), _USER, object(), object(), object()),
            422,
        ),
        (
            '/mentor-sessions/{session_id}/attachments/{attachment_id}/file',
            'GET',
            ('invalid', _VALID_ULID, _USER, object(), object(), object(), object()),
            422,
        ),
    ],
)
def test_attachment_routes_reject_malformed_ids_inside_handlers(
    path: str,
    method: str,
    args: tuple[object, ...],
    expected_status: int,
) -> None:
    router = APIRouter()
    MentorAttachmentsController.handle(router)
    endpoint = _endpoint(router, path, method)

    with pytest.raises(HTTPException) as error:
        endpoint(*args)

    assert error.value.status_code == expected_status


@pytest.mark.parametrize(
    ('content_length', 'expected_status'),
    [('invalid', 422), ('10065000', 413)],
)
@pytest.mark.anyio
async def test_upload_route_rejects_invalid_declared_lengths_inside_handler(
    content_length: str,
    expected_status: int,
) -> None:
    router = APIRouter()
    MentorAttachmentsController.handle(router)
    endpoint = _endpoint(
        router,
        '/mentor-attachment-batches/{batch_id}/attachments',
        'POST',
    )
    request = StarletteRequest(
        {
            'type': 'http',
            'method': 'POST',
            'path': '/',
            'headers': [(b'content-length', content_length.encode())],
        }
    )

    with pytest.raises(HTTPException) as error:
        await endpoint(  # type: ignore[operator]
            _VALID_ULID,
            request,
            Response(),
            UploadFile(file=BytesIO(b'content'), filename='notes.txt'),
            uuid4(),
            _USER,
            object(),
            object(),
            object(),
            object(),
            object(),
            object(),
        )

    assert error.value.status_code == expected_status

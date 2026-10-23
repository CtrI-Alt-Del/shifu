from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.routing import APIRoute
from shifu.intelligence.rest.controllers.upload_mentor_attachment_controller import (
    UploadMentorAttachmentController,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

_BATCH_ID = '0' * 25 + '1'
_UPLOAD_PATH = f'/intelligence/mentor-attachment-batches/{_BATCH_ID}/attachments'
_MAX_MULTIPART_BYTES = 2_064_000


def test_upload_body_limit_rejects_invalid_content_length(client: TestClient) -> None:
    response = client.post(
        _UPLOAD_PATH,
        content=b'',
        headers={'content-length': 'invalid'},
    )

    assert response.status_code == 400
    assert response.json() == {
        'code': 'malformed_attachment',
        'message': 'Não foi possível ler este arquivo.',
    }
    assert response.headers['cache-control'] == 'no-store'


def test_upload_body_limit_rejects_negative_content_length(client: TestClient) -> None:
    response = client.post(
        _UPLOAD_PATH,
        content=b'',
        headers={'content-length': '-1'},
    )

    assert response.status_code == 400
    assert response.json()['code'] == 'malformed_attachment'


def test_upload_body_limit_rejects_oversized_content_length(client: TestClient) -> None:
    response = client.post(
        _UPLOAD_PATH,
        content=b'',
        headers={'content-length': str(_MAX_MULTIPART_BYTES + 1)},
    )

    assert response.status_code == 413
    assert response.json() == {
        'code': 'attachment_too_large',
        'message': 'O arquivo excede o limite de 2 MB.',
    }


def test_upload_body_limit_counts_streamed_body_without_content_length(
    client: TestClient,
) -> None:
    body: Iterator[bytes] = iter((b'x' * 1_032_001, b'x' * 1_032_000))

    response = client.post(_UPLOAD_PATH, content=body)

    assert response.status_code == 413
    assert response.json()['code'] == 'attachment_too_large'


def test_upload_body_limit_does_not_apply_to_other_methods_or_paths(
    client: TestClient,
) -> None:
    headers = {'content-length': str(_MAX_MULTIPART_BYTES + 1)}

    method_response = client.get(_UPLOAD_PATH, headers=headers)
    path_response = client.post(
        '/intelligence/mentor-attachment-batches/not-an-upload',
        content=b'',
        headers=headers,
    )

    assert method_response.status_code == 405
    assert path_response.status_code == 405


def test_upload_handler_is_synchronous_so_blocking_work_leaves_the_event_loop() -> None:
    router = APIRouter()
    UploadMentorAttachmentController.handle(router)

    routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute)
        and route.path == '/mentor-attachment-batches/{batch_id}/attachments'
        and 'POST' in (route.methods or set())
    ]

    assert len(routes) == 1
    assert not inspect.iscoroutinefunction(routes[0].endpoint)

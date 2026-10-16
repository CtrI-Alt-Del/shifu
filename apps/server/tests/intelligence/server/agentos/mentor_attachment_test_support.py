"""Public-boundary helpers shared by the registered attachment tests."""

from __future__ import annotations

from time import monotonic, sleep
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


ATTACHMENT_TEXT = 'Documento privado: uma fracção equivalente preserva a quantidade.'
MODEL_ANSWER = 'O trecho anexado explica o conceito solicitado.'


def create_session(client: TestClient) -> str:
    response = client.post(
        '/intelligence/mentor-sessions',
        json={
            'submission_key': str(uuid4()),
            'first_message': 'Quais Habilidades já concluí?',
        },
    )
    assert response.status_code == 201, response.text
    return response.json()['session']['id']


def create_goal(client: TestClient) -> str:
    response = client.post(
        '/learning/goals',
        json={
            'title': 'Estudar frações',
            'description': 'Compreender como comparar frações equivalentes.',
            'skillIds': [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()['goalId']


def upload_ready_text_attachment(
    client: TestClient,
    *,
    session_id: str,
) -> tuple[str, str]:
    batch_response = client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']

    upload_response = client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={
            'file': (
                'lesson.txt',
                ATTACHMENT_TEXT.encode(),
                'text/plain',
            )
        },
    )
    assert upload_response.status_code == 201, upload_response.text
    attachment_id = upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    last_response = upload_response.text
    while monotonic() < deadline:
        response = client.get(f'/intelligence/mentor-attachment-batches/{batch_id}')
        assert response.status_code == 200, response.text
        last_response = response.text
        attachments = response.json()['attachments']
        status = attachments[0]['status']
        if status in {'ready', 'failed'}:
            assert status == 'ready', response.text
            return batch_id, attachment_id
        sleep(0.75)

    pytest.fail(
        'Registered attachment workflow did not reach a terminal state: '
        f'{last_response}'
    )


def submit_message_with_attachment(
    client: TestClient,
    *,
    session_id: str,
    batch_id: str,
    attachment_id: str,
    goal_id: str,
) -> str:
    response = client.post(
        f'/intelligence/mentor-sessions/{session_id}/messages',
        json={
            'submission_key': str(uuid4()),
            'content': 'Quero conversar sobre como estudar usando o documento anexado.',
            'context_hint': {'goal_id': goal_id},
            'attachment_batch_id': batch_id,
            'attachment_ids': [attachment_id],
        },
    )
    assert response.status_code == 202, response.text
    return response.json()['response']['attempt_id']


def wait_for_session_response(
    client: TestClient,
    session_id: str,
    attempt_id: str | None = None,
) -> dict[str, object]:
    deadline = monotonic() + 45
    while monotonic() < deadline:
        response = client.get(f'/intelligence/mentor-sessions/{session_id}')
        assert response.status_code == 200, response.text
        body = response.json()
        snapshot = cast('dict[str, object]', body['response'])
        if attempt_id is not None and snapshot['attempt_id'] != attempt_id:
            sleep(0.75)
            continue
        status = snapshot['status']
        if status in {'completed', 'failed', 'cancelled'}:
            return body
        sleep(0.75)

    pytest.fail('Registered response workflow did not reach a terminal state')

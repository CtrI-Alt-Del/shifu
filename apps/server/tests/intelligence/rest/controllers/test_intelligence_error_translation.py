from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_SESSIONS_PATH = '/intelligence/mentor-sessions'
_MEMORIES_PATH = '/intelligence/learner-memories'
_UNKNOWN_SESSION_ID = '0' * 25 + '1'
_VALIDATION_ERROR = {
    'code': 'validation_error',
    'message': 'Os dados enviados são inválidos.',
}
_INVALID_CURSOR = {'code': 'validation_error', 'message': 'Cursor inválido.'}


class TestIntelligenceErrorTranslation:
    def test_should_translate_a_malformed_cursor_on_the_session_list(
        self, mentor_client: TestClient
    ) -> None:
        response = mentor_client.get(_SESSIONS_PATH, params={'cursor': 'not-a-cursor'})

        assert response.status_code == 422
        assert response.json() == _INVALID_CURSOR

    def test_should_translate_an_empty_cursor_on_the_session_list(
        self, mentor_client: TestClient
    ) -> None:
        response = mentor_client.get(_SESSIONS_PATH, params={'cursor': ''})

        assert response.status_code == 422
        assert response.json() == _INVALID_CURSOR

    def test_should_translate_a_malformed_cursor_on_the_session_detail(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            _SESSIONS_PATH,
            json={
                'submission_key': '19c0e33a-e8db-4cf5-8a0c-999999999998',
                'first_message': 'Pergunta com cursor inválido.',
            },
        )
        assert created.status_code == 201

        response = mentor_client.get(
            f'{_SESSIONS_PATH}/{created.json()["session"]["id"]}',
            params={'cursor': 'not-a-cursor'},
        )

        assert response.status_code == 422
        assert response.json() == _INVALID_CURSOR

    @pytest.mark.parametrize('method', ['GET', 'PATCH', 'DELETE'])
    def test_should_reject_a_malformed_session_id_through_request_validation(
        self, mentor_client: TestClient, method: str
    ) -> None:
        response = mentor_client.request(
            method, f'{_SESSIONS_PATH}/not-a-ulid', json={'title': 'Novo título'}
        )

        assert response.status_code == 422
        assert response.json() == _VALIDATION_ERROR

    @pytest.mark.parametrize(
        ('method', 'body', 'expected_status'),
        [('GET', None, 404), ('PATCH', {'title': 'Novo título'}, 404)],
    )
    def test_should_accept_a_well_formed_session_id_and_hide_unknown_sessions(
        self,
        mentor_client: TestClient,
        method: str,
        body: dict[str, str] | None,
        expected_status: int,
    ) -> None:
        response = mentor_client.request(
            method, f'{_SESSIONS_PATH}/{_UNKNOWN_SESSION_ID}', json=body
        )

        assert response.status_code == expected_status
        assert response.json()['code'] == 'not_found'

    def test_should_reject_an_oversized_learner_memory_search(
        self, mentor_client: TestClient
    ) -> None:
        oversized = mentor_client.get(_MEMORIES_PATH, params={'q': 'a' * 101})
        limit = mentor_client.get(_MEMORIES_PATH, params={'q': 'a' * 100})

        assert oversized.status_code == 422
        assert oversized.json()['code'] == 'validation_error'
        assert limit.status_code == 200
        assert limit.json() == {'items': []}

    @pytest.mark.parametrize('content', ['', '    ', 'x' * 281])
    def test_should_translate_invalid_learner_memory_content_into_a_422(
        self, mentor_client: TestClient, content: str
    ) -> None:
        response = mentor_client.patch(
            f'{_MEMORIES_PATH}/{_UNKNOWN_SESSION_ID}',
            json={'content': content, 'expected_version': 1},
        )

        assert response.status_code == 422
        assert response.json() == {
            'code': 'validation_error',
            'message': 'O texto da memória deve ter entre 1 e 280 caracteres.',
        }

    def test_should_start_a_planning_session_with_an_iso_timestamp(
        self, mentor_client: TestClient
    ) -> None:
        response = mentor_client.post(
            '/intelligence/planning-sessions',
            json={'initial_intent': '  Aprender Python  '},
        )

        assert response.status_code == 201
        body = response.json()
        assert set(body) == {'id', 'created_at'}
        assert isinstance(body['id'], str)
        assert (
            body['created_at'] == datetime.fromisoformat(body['created_at']).isoformat()
        )

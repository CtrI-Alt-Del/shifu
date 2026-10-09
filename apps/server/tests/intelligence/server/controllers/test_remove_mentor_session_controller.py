from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx import Response


class TestRemoveMentorSessionController:
    def test_should_reject_malformed_session_id(
        self, mentor_client: TestClient
    ) -> None:
        response = cast(
            'Response', mentor_client.delete('/intelligence/mentor-sessions/not-a-ulid')
        )

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_delete_confirmed_session_idempotently_and_prevent_replay(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': 'e57256c2-51c4-4d62-82d6-999999999999',
                'first_message': 'Mensagem privada.',
            },
        )
        session_id = created.json()['session']['id']
        path = f'/intelligence/mentor-sessions/{session_id}'

        deleted = cast('Response', mentor_client.delete(path))
        repeated = cast('Response', mentor_client.delete(path))
        missing = cast('Response', mentor_client.get(path))
        replay = cast(
            'Response',
            mentor_client.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': 'e57256c2-51c4-4d62-82d6-999999999999',
                    'first_message': 'Mensagem privada.',
                },
            ),
        )
        listed = mentor_client.get('/intelligence/mentor-sessions')

        assert deleted.status_code == 204
        assert deleted.headers['cache-control'] == 'private, no-store'
        assert repeated.status_code == 204
        assert missing.status_code == 404
        assert replay.status_code == 404
        assert session_id not in [item['id'] for item in listed.json()['items']]

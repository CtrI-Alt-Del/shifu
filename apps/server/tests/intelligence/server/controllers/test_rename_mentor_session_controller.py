from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx import Response


class TestRenameMentorSessionController:
    def test_should_reject_malformed_session_id(
        self, mentor_client: TestClient
    ) -> None:
        response = cast(
            'Response',
            mentor_client.patch(
                '/intelligence/mentor-sessions/not-a-ulid',
                json={'title': 'Valid title'},
            ),
        )

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_trim_title_and_update_search_results(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': 'a9a77df5-2aa7-46ef-8e40-999999999999',
                'first_message': 'Mensagem.',
            },
        )
        session_id = created.json()['session']['id']
        renamed = cast(
            'Response',
            mentor_client.patch(
                f'/intelligence/mentor-sessions/{session_id}',
                json={'title': '  Álgebra e funções  '},
            ),
        )

        assert renamed.status_code == 200
        assert renamed.json()['title'] == 'Álgebra e funções'
        matches = mentor_client.get(
            '/intelligence/mentor-sessions', params={'search': 'algebra'}
        )
        assert [item['id'] for item in matches.json()['items']] == [session_id]

    def test_should_reject_invalid_title_without_changing_active_session(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': 'a9a77df5-2aa7-46ef-8e40-888888888888',
                'first_message': 'Mensagem.',
            },
        )
        session_id = created.json()['session']['id']
        response = cast(
            'Response',
            mentor_client.patch(
                f'/intelligence/mentor-sessions/{session_id}', json={'title': '  '}
            ),
        )
        current = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')

        assert response.status_code == 422
        assert current.json()['session']['title'] == 'Conversa de teste'

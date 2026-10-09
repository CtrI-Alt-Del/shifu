import base64
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.pipes import SharedPipe
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT

if TYPE_CHECKING:
    from httpx import Response


class TestGetMentorSessionController:
    def test_should_return_only_owned_active_session_and_accepted_message(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': '89c0e33a-e8db-4cf5-8a0c-999999999999',
                'first_message': 'Quero aprender matemática.',
            },
        )
        session_id = created.json()['session']['id']

        response = cast(
            'Response',
            mentor_client.get(f'/intelligence/mentor-sessions/{session_id}'),
        )
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.json()['session']['id'] == session_id
        assert response.json()['messages']['items'][0]['content'] == (
            'Quero aprender matemática.'
        )

    def test_should_return_newest_message_pages_in_chronological_order_and_pending_state(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': '09c0e33a-e8db-4cf5-8a0c-999999999999',
                'first_message': 'Primeira pergunta aceita.',
            },
        )
        session_id = created.json()['session']['id']
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        identifiers = SystemIdentifierProvider()
        first_timestamp = datetime(2026, 1, 1, tzinfo=UTC)
        seeded_ids: list[str] = []
        with database.transaction() as repositories:
            for index in range(30):
                learner_id = identifiers.generate()
                seeded_ids.append(learner_id)
                repositories.mentor_messages.add(
                    MentorMessage(
                        id=learner_id,
                        session_id=session_id,
                        role=MentorMessageRole.LEARNER,
                        content=f'Pergunta de histórico {index}.',
                        created_at=first_timestamp + timedelta(seconds=index * 2),
                        in_reply_to_message_id=None,
                    )
                )
                if index == 0:
                    repositories.mentor_messages.add(
                        MentorMessage(
                            id=identifiers.generate(),
                            session_id=session_id,
                            role=MentorMessageRole.MENTOR,
                            content='Resposta persistida.',
                            created_at=first_timestamp + timedelta(seconds=1),
                            in_reply_to_message_id=learner_id,
                        )
                    )

        first_page = cast(
            'Response',
            mentor_client.get(f'/intelligence/mentor-sessions/{session_id}'),
        )
        assert first_page.status_code == 200
        page_body = first_page.json()
        assert len(page_body['messages']['items']) == 30
        assert page_body['messages']['items'][0]['content'] == (
            'Pergunta de histórico 1.'
        )
        assert page_body['messages']['items'][-1]['content'] == (
            'Primeira pergunta aceita.'
        )
        assert page_body['messages']['next_cursor'] is not None
        assert (
            page_body['pending_learner_message_id']
            == page_body['messages']['items'][-1]['id']
        )

        older_page = cast(
            'Response',
            mentor_client.get(
                f'/intelligence/mentor-sessions/{session_id}',
                params={'cursor': page_body['messages']['next_cursor']},
            ),
        )
        assert older_page.status_code == 200
        older_items = older_page.json()['messages']['items']
        assert len(older_items) == 2
        assert [item['content'] for item in older_items] == [
            'Pergunta de histórico 0.',
            'Resposta persistida.',
        ]

    def test_should_reject_malformed_message_cursor_as_validation_error(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': '19c0e33a-e8db-4cf5-8a0c-999999999999',
                'first_message': 'Pergunta com cursor inválido.',
            },
        )
        response = cast(
            'Response',
            mentor_client.get(
                f'/intelligence/mentor-sessions/{created.json()["session"]["id"]}',
                params={'cursor': 'not-a-cursor'},
            ),
        )

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_reject_cursor_for_a_different_resource(
        self, mentor_client: TestClient
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': '44c0e33a-e8db-4cf5-8a0c-999999999999',
                'first_message': 'Pergunta para validar o cursor.',
            },
        )
        payload = json.dumps(
            {
                'kind': 'sessions',
                'account_id': MENTOR_ACCOUNT.account_id,
                'session_id': created.json()['session']['id'],
                'created_at': datetime.now(UTC).isoformat(),
                'id': '01JMESSAGE000000000000000000',
            },
            separators=(',', ':'),
        ).encode()
        cursor = base64.urlsafe_b64encode(payload).decode().rstrip('=')

        response = cast(
            'Response',
            mentor_client.get(
                f'/intelligence/mentor-sessions/{created.json()["session"]["id"]}',
                params={'cursor': cursor},
            ),
        )

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_hide_unknown_ids_and_reject_invalid_ulids(
        self, mentor_client: TestClient
    ) -> None:
        unknown = cast(
            'Response',
            mentor_client.get(
                '/intelligence/mentor-sessions/00000000000000000000000000'
            ),
        )
        malformed = cast(
            'Response', mentor_client.get('/intelligence/mentor-sessions/not-a-ulid')
        )

        assert unknown.status_code == 404
        assert malformed.status_code == 422

    def test_should_return_private_not_found_for_another_authenticated_account(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        created = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': 'f50d79e9-bc83-40fb-9fc9-999999999999',
                'first_message': 'Dados privados.',
            },
        )
        other_app = FastAPIApp.register(postgres_database.engine)
        other_user = AuthenticatedUser(
            account_id='01JOTHER000000000000TEST',
            display_name='Other Learner',
            time_zone=None,
        )
        other_app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            other_user
        )
        with TestClient(
            other_app, headers={'Authorization': 'Bearer test-token'}
        ) as client:
            response = cast(
                'Response',
                client.get(
                    f'/intelligence/mentor-sessions/{created.json()["session"]["id"]}'
                ),
            )

        assert response.status_code == 404
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_require_authentication_for_private_history(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            response = cast(
                'Response',
                client.get('/intelligence/mentor-sessions/00000000000000000000000000'),
            )

        assert response.status_code == 401
        assert response.headers['cache-control'] == 'private, no-store'

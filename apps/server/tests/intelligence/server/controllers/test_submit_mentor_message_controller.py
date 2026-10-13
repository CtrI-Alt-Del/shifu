from fastapi.testclient import TestClient

from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    create_session,
    complete_response,
)


class TestSubmitMentorMessageController:
    def test_should_persist_subsequent_text_and_replay_once(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, attempt, learner)
        payload = {
            'submission_key': '223e4567-e89b-42d3-a456-426614174000',
            'content': '  Texto exato\nsegunda mensagem  ',
            'context_hint': None,
        }
        accepted = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages', json=payload
        )
        replay = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages', json=payload
        )
        assert accepted.status_code == 202
        assert replay.status_code == 200
        assert accepted.headers['cache-control'] == 'private, no-store'
        assert (
            replay.json()['response']['attempt_id']
            == accepted.json()['response']['attempt_id']
        )
        assert accepted.json()['response']['status'] == 'queued'
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            messages = repositories.mentor_messages.find_all(
                MENTOR_ACCOUNT.account_id, session
            )
            current = repositories.mentor_response_attempts.find_current(
                MENTOR_ACCOUNT.account_id, session
            )
            assert len(messages) == 3
            assert messages[-1].content == payload['content']
            assert current is not None
            assert current.id == accepted.json()['response']['attempt_id']

    def test_should_reject_distinct_submit_with_pending_learner(
        self, mentor_client: TestClient
    ) -> None:
        session, _, _ = create_session(mentor_client)
        response = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages',
            json={
                'submission_key': '223e4567-e89b-42d3-a456-426614174000',
                'content': 'Outra mensagem',
            },
        )
        assert response.status_code == 409
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_reject_foreign_resource_and_extra_fields(
        self, mentor_client: TestClient
    ) -> None:
        unknown = mentor_client.post(
            '/intelligence/mentor-sessions/00000000000000000000000000/messages',
            json={
                'submission_key': '223e4567-e89b-42d3-a456-426614174000',
                'content': 'texto',
            },
        )
        malformed = mentor_client.post(
            '/intelligence/mentor-sessions/not-ulid/messages',
            json={
                'submission_key': '223e4567-e89b-42d3-a456-426614174000',
                'content': 'texto',
                'account_id': 'forged',
            },
        )
        assert unknown.status_code == 404
        assert malformed.status_code == 422

    def test_should_reject_whitespace_message_without_persisting_submission(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        response = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages',
            json={
                'submission_key': '223e4567-e89b-42d3-a456-426614174000',
                'content': ' \n\t ',
            },
        )
        assert response.status_code == 422
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            assert (
                len(
                    repositories.mentor_messages.find_all(
                        MENTOR_ACCOUNT.account_id, session
                    )
                )
                == 1
            )
            current = repositories.mentor_response_attempts.find_current(
                MENTOR_ACCOUNT.account_id, session
            )
            assert current is not None
            assert current.id == attempt
            assert current.learner_message_id == learner
            assert (
                repositories.mentor_response_attempts.find_submission(
                    MENTOR_ACCOUNT.account_id,
                    session,
                    '223e4567-e89b-42d3-a456-426614174000',
                )
                is None
            )

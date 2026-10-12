from fastapi.testclient import TestClient

from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    create_session,
)


class TestRetryMentorResponseController:
    def test_should_retry_same_learner_with_new_attempt_and_replay(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        cancelled = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/responses/{attempt}/cancel',
            json={'submission_key': '223e4567-e89b-42d3-a456-426614174000'},
        )
        assert cancelled.status_code == 200
        url = f'/intelligence/mentor-sessions/{session}/responses/{attempt}/retry'
        payload = {'submission_key': '323e4567-e89b-42d3-a456-426614174000'}
        first = mentor_client.post(url, json=payload)
        replay = mentor_client.post(url, json=payload)
        assert first.status_code == 202
        assert replay.status_code == 200
        assert first.json()['attempt_id'] != attempt
        assert replay.json()['attempt_id'] == first.json()['attempt_id']
        assert first.json()['learner_message_id'] == learner
        assert first.json()['status'] == 'queued'
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
            assert current is not None and current.id == first.json()['attempt_id']

    def test_should_reject_retry_of_queued_response(
        self, mentor_client: TestClient
    ) -> None:
        session, attempt, _ = create_session(mentor_client)
        result = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/responses/{attempt}/retry',
            json={'submission_key': '223e4567-e89b-42d3-a456-426614174000'},
        )
        assert result.status_code == 409

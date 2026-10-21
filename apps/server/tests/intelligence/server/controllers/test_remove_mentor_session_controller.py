from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    append_status,
    create_session,
    start_processing,
)
from tests.intelligence.server.controllers.mentor_summary_scenarios import (
    count_summaries,
    seed_exchanges,
    seed_summary,
)
from shifu.intelligence.core.domain.entities import MentorSessionSummary
from shifu.intelligence.core.domain.enums import MentorWorkflowStep
from shifu.intelligence.core.domain.structures import MentorSummaryBoundary
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase

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


class TestRemoveMentorSessionControllerSummaries:
    def test_should_remove_ready_and_processing_summary_rows_with_the_conversation(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, _ = create_session(mentor_client)
        start_processing(postgres_database, attempt_id)
        append_status(
            postgres_database,
            session_id,
            attempt_id,
            MentorWorkflowStep.SUMMARIZE_CONTEXT,
        )
        messages = seed_exchanges(postgres_database, session_id, 3)
        seed_summary(postgres_database, session_id, attempt_id, messages, version=1)
        processing = MentorSessionSummary.start(
            id=SystemIdentifierProvider().generate(),
            account_id=MENTOR_ACCOUNT.account_id,
            session_id=session_id,
            attempt_id=attempt_id,
            version=2,
            boundary=MentorSummaryBoundary(
                message_id=messages[-1].id, created_at=messages[-1].created_at
            ),
            covered_message_count=6,
            first_message_id=messages[0].id,
            now=messages[-1].created_at,
        )
        # A processing row requires its attempt; deletion must still succeed.
        with SqlalchemyIntelligenceDatabase(postgres_database.engine).transaction() as (
            repositories
        ):
            repositories.mentor_session_summaries.add(processing)
        assert count_summaries(postgres_database, session_id) == 2

        deleted = mentor_client.delete(f'/intelligence/mentor-sessions/{session_id}')

        assert deleted.status_code == 204
        assert count_summaries(postgres_database, session_id) == 0
        assert (
            mentor_client.get(
                f'/intelligence/mentor-sessions/{session_id}/summary'
            ).status_code
            == 404
        )
        repeated = mentor_client.delete(f'/intelligence/mentor-sessions/{session_id}')
        assert repeated.status_code == 204

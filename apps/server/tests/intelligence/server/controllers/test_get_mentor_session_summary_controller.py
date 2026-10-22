from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.core.domain.enums import MentorSummaryFailureCode
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import configure_mentor_access
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    create_session,
)
from tests.intelligence.server.controllers.mentor_summary_scenarios import (
    LEARNER_TEXT,
    MENTOR_TEXT,
    seed_exchanges,
    seed_summary,
)

if TYPE_CHECKING:
    from httpx import Response

_NOT_FOUND = {'code': 'not_found', 'message': 'Resumo da conversa não encontrado.'}


class TestGetMentorSessionSummaryController:
    def test_should_return_the_rendered_summary_without_offsets(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, _ = create_session(mentor_client)
        messages = seed_exchanges(postgres_database, session_id, 3)
        seed_summary(postgres_database, session_id, attempt_id, messages, version=2)

        response = cast(
            'Response',
            mentor_client.get(f'/intelligence/mentor-sessions/{session_id}/summary'),
        )

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.json() == {
            'version': 2,
            'text': (
                'Nesta conversa, os assuntos foram range e lista. '
                f'Você perguntou: “{LEARNER_TEXT}” '
                f'O Mentor orientou: “{MENTOR_TEXT}”'
            ),
            'covered_message_count': 6,
            'first_message_id': messages[0].id,
        }
        assert set(response.json()) == {
            'version',
            'text',
            'covered_message_count',
            'first_message_id',
        }

    def test_should_answer_the_same_not_found_for_absent_summary_unknown_foreign_and_deleted_sessions(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, _ = create_session(mentor_client)
        deleted_id, deleted_attempt, _ = create_session(
            mentor_client, '223e4567-e89b-42d3-a456-426614174000'
        )
        messages = seed_exchanges(postgres_database, deleted_id, 2)
        seed_summary(postgres_database, deleted_id, deleted_attempt, messages)
        assert (
            mentor_client.delete(
                f'/intelligence/mentor-sessions/{deleted_id}'
            ).status_code
            == 204
        )
        other_app = FastAPIApp.register(postgres_database.engine)
        configure_mentor_access(other_app)
        other_app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id='01JOTHER000000000000TEST',
                display_name='Other Learner',
                time_zone=None,
            )
        )
        own_messages = seed_exchanges(postgres_database, session_id, 2)
        seed_summary(postgres_database, session_id, attempt_id, own_messages)

        bodies: list[dict[str, str]] = []
        for client_paths in (
            (mentor_client, '00000000000000000000000000'),
            (mentor_client, deleted_id),
        ):
            client, target = client_paths
            response = cast(
                'Response',
                client.get(f'/intelligence/mentor-sessions/{target}/summary'),
            )
            assert response.status_code == 404
            assert response.headers['cache-control'] == 'private, no-store'
            bodies.append(response.json())
        with TestClient(
            other_app, headers={'Authorization': 'Bearer test-token'}
        ) as other:
            foreign = cast(
                'Response',
                other.get(f'/intelligence/mentor-sessions/{session_id}/summary'),
            )
        assert foreign.status_code == 404
        bodies.append(foreign.json())

        assert bodies == [_NOT_FOUND, _NOT_FOUND, _NOT_FOUND]

    def test_should_not_expose_processing_or_failed_summaries(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, _ = create_session(mentor_client)
        messages = seed_exchanges(postgres_database, session_id, 2)
        seed_summary(
            postgres_database,
            session_id,
            attempt_id,
            messages,
            failure=MentorSummaryFailureCode.NLP_UNAVAILABLE,
        )

        response = cast(
            'Response',
            mentor_client.get(f'/intelligence/mentor-sessions/{session_id}/summary'),
        )

        assert response.status_code == 404
        assert response.json() == _NOT_FOUND

    def test_should_reject_malformed_session_ids(
        self, mentor_client: TestClient
    ) -> None:
        response = cast(
            'Response',
            mentor_client.get('/intelligence/mentor-sessions/not-a-ulid/summary'),
        )

        assert response.status_code == 422

    def test_should_require_authentication(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app, headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret}
        ) as client:
            response = cast(
                'Response',
                client.get(
                    '/intelligence/mentor-sessions/00000000000000000000000000/summary'
                ),
            )

        assert response.status_code == 401

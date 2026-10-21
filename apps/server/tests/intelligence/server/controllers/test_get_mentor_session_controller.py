import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.pipes import SharedPipe
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import (
    MENTOR_ACCOUNT,
    configure_mentor_access,
)
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    append_status,
    create_session,
    start_processing,
)
from tests.intelligence.server.controllers.mentor_summary_scenarios import (
    seed_exchanges,
    seed_summary,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryChangeKind,
    MentorSummaryFailureCode,
    MentorWorkflowStep,
)
from tests.intelligence.server.controllers.learner_memory_scenarios import (
    BASE_TIME,
    OTHER_ACCOUNT,
    iso,
    seed_change,
    seed_conversation,
    seed_memory,
)

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
        configure_mentor_access(other_app)
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

    def test_should_preserve_answered_legacy_history_without_response_attempt(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        identifiers = SystemIdentifierProvider()
        session_id, learner_id, reply_id = (
            identifiers.generate(),
            identifiers.generate(),
            identifiers.generate(),
        )
        created_at = datetime(2025, 1, 1, tzinfo=UTC)
        question = 'Como organizar meus estudos?'
        answer = 'Reserve um horário para revisar o que aprendeu.'
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        # e633 backfills attempts only for unanswered legacy learners. This
        # already answered conversation legitimately has no response attempt.
        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=MENTOR_ACCOUNT.account_id,
                    title='Conversa anterior',
                    created_at=created_at,
                    updated_at=created_at + timedelta(seconds=1),
                    last_activity_at=created_at + timedelta(seconds=1),
                ),
                'legacy:' + session_id,
                hashlib.sha256(question.encode()).hexdigest(),
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=learner_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content=question,
                    created_at=created_at,
                    in_reply_to_message_id=None,
                )
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=reply_id,
                    session_id=session_id,
                    role=MentorMessageRole.MENTOR,
                    content=answer,
                    created_at=created_at + timedelta(seconds=1),
                    in_reply_to_message_id=learner_id,
                )
            )
        response = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert body['session']['id'] == session_id
        assert body['response'] is None
        assert body['pending_learner_message_id'] is None
        assert body['messages']['next_cursor'] is None
        assert [
            (item['id'], item['role'], item['content'])
            for item in body['messages']['items']
        ] == [(learner_id, 'learner', question), (reply_id, 'mentor', answer)]


class TestGetMentorSessionControllerSummaryState:
    def test_should_return_an_empty_summary_state_without_summaries(
        self, mentor_client: TestClient
    ) -> None:
        session_id, _, _ = create_session(mentor_client)

        body = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}').json()

        assert body['summary'] == {'current': None, 'failure_after_message_id': None}

    def test_should_expose_the_ready_marker_without_content_or_offsets(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, learner_id = create_session(mentor_client)
        messages = seed_exchanges(postgres_database, session_id, 3)
        summary = seed_summary(
            postgres_database, session_id, attempt_id, messages, version=2
        )

        response = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')

        assert response.status_code == 200
        current = response.json()['summary']['current']
        assert current == {
            'version': 2,
            'boundary_message_id': messages[-1].id,
            'covered_message_count': 6,
            'completed_at': summary.completed_at.isoformat().replace('+00:00', 'Z')
            if summary.completed_at
            else None,
            'after_message_id': learner_id,
        }
        assert response.json()['summary']['failure_after_message_id'] is None
        for hidden in ('excerpts', 'topics', 'start', 'algorithm_version'):
            assert hidden not in response.json()['summary']['current']

    def test_should_anchor_the_failure_notice_after_the_failed_attempts_learner_message(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, learner_id = create_session(mentor_client)
        messages = seed_exchanges(postgres_database, session_id, 2)
        seed_summary(
            postgres_database,
            session_id,
            attempt_id,
            messages,
            failure=MentorSummaryFailureCode.NLP_UNAVAILABLE,
        )

        body = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}').json()

        assert body['summary'] == {
            'current': None,
            'failure_after_message_id': learner_id,
        }

    def test_should_report_progress_of_the_latest_status_event_including_null(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, attempt_id, _ = create_session(mentor_client)
        start_processing(postgres_database, attempt_id)
        path = f'/intelligence/mentor-sessions/{session_id}'

        expected = [
            (MentorWorkflowStep.SUMMARIZE_CONTEXT, 'summarize-context'),
            (None, None),
            (MentorWorkflowStep.WRITE_ANSWER, 'write-answer'),
            (MentorWorkflowStep.REVIEW_ANSWER, 'review-answer'),
        ]
        for step, progress in expected:
            append_status(postgres_database, session_id, attempt_id, step)
            assert mentor_client.get(path).json()['response']['progress'] == progress


class TestGetMentorSessionControllerMemoryItems:
    def test_should_expose_an_empty_memory_item_list_without_changes(
        self, mentor_client: TestClient
    ) -> None:
        session_id, _, _ = create_session(mentor_client)

        body = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}').json()

        assert body['memory_items'] == []

    def test_should_expose_every_change_record_of_the_whole_conversation_in_order(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        created = seed_memory(
            postgres_database,
            1,
            content='Prefiro exemplos em Python.',
            origins=((session_id, message_id),),
        )
        updated = seed_memory(
            postgres_database,
            2,
            content='Agora prefiro JavaScript.',
            origins=((session_id, message_id),),
        )
        first = seed_change(
            postgres_database,
            created,
            session_id,
            message_id,
            created_at=BASE_TIME,
        )
        second = seed_change(
            postgres_database,
            updated,
            session_id,
            message_id,
            kind=LearnerMemoryChangeKind.UPDATED,
            previous_content='Prefiro Python.',
            created_at=BASE_TIME + timedelta(minutes=1),
        )

        response = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.json()['memory_items'] == [
            {
                'id': first,
                'source_message_id': message_id,
                'kind': 'created',
                'category': 'explanation_preference',
                'memory_id': created.id,
                'content': 'Prefiro exemplos em Python.',
                'previous_content': None,
                'created_at': iso(BASE_TIME),
            },
            {
                'id': second,
                'source_message_id': message_id,
                'kind': 'updated',
                'category': 'explanation_preference',
                'memory_id': updated.id,
                'content': 'Agora prefiro JavaScript.',
                'previous_content': 'Prefiro Python.',
                'created_at': iso(BASE_TIME + timedelta(minutes=1)),
            },
        ]

    def test_should_show_deleted_memory_items_without_text_or_memory_reference(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        memory = seed_memory(postgres_database, 1, origins=((session_id, message_id),))
        change_id = seed_change(postgres_database, memory, session_id, message_id)

        mentor_client.delete(f'/intelligence/learner-memories/{memory.id}')
        body = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}').json()

        assert body['memory_items'] == [
            {
                'id': change_id,
                'source_message_id': message_id,
                'kind': 'created',
                'category': 'explanation_preference',
                'memory_id': None,
                'content': None,
                'previous_content': None,
                'created_at': iso(BASE_TIME),
            }
        ]

    def test_should_not_expose_the_change_records_of_another_accounts_conversation(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(
            postgres_database, OTHER_ACCOUNT.account_id
        )
        memory = seed_memory(
            postgres_database,
            1,
            account_id=OTHER_ACCOUNT.account_id,
            origins=((session_id, message_id),),
        )
        seed_change(postgres_database, memory, session_id, message_id)

        response = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')

        assert response.status_code == 404
        assert 'memory_items' not in response.json()

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    complete_response,
    create_session,
)


class TestSubmitMentorMessageController:
    @pytest.mark.parametrize('content', ['', ' \n\t '])
    @pytest.mark.parametrize(
        'status', [MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL]
    )
    def test_should_persist_and_replay_attachment_only_message(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        content: str,
        status: MentorAttachmentStatus,
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, attempt, learner)
        ids = SystemIdentifierProvider()
        now = datetime.now(UTC)
        batch = MentorAttachmentBatch.create(
            ids.generate(),
            MENTOR_ACCOUNT.account_id,
            session,
            now,
            now + timedelta(hours=1),
        )
        attachment = MentorAttachment.create(
            attachment_id=ids.generate(),
            account_id=MENTOR_ACCOUNT.account_id,
            batch_id=batch.id,
            upload_key='controlled-upload',
            filename='image.png',
            media_type='image/png',
            size_bytes=20,
            checksum='a' * 64,
            object_key='private/controlled-image.png',
            now=now,
        )
        attachment.status = status
        database = SqlalchemyIntelligenceDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.mentor_attachment_batches.add(batch)
            repositories.mentor_attachments.add(attachment)
        payload = {
            'submission_key': '76f06641-8074-4314-99ed-a6cc7c981080',
            'content': content,
            'attachment_batch_id': batch.id,
            'attachment_ids': [attachment.id],
        }

        response = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages', json=payload
        )
        replay = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages', json=payload
        )

        assert response.status_code == 202
        assert replay.status_code == 200
        body = response.json()
        session_id = body['session']['id']
        assert replay.json()['session']['id'] == session_id
        with database.transaction() as repositories:
            messages = repositories.mentor_messages.find_all(
                MENTOR_ACCOUNT.account_id, session_id
            )
            sent = tuple(message for message in messages if message.attachments)
            persisted_batch = repositories.mentor_attachment_batches.find_by_id(
                batch.id
            )
        assert len(sent) == 1
        assert sent[0].content == content
        assert sent[0].attachments[0].attachment_id == attachment.id
        assert sent[0].attachments[0].status is status
        assert persisted_batch is not None
        assert persisted_batch.consumed_by_message_id == sent[0].id
        detail = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')
        assert detail.status_code == 200
        stored = next(
            message
            for message in detail.json()['messages']['items']
            if message['id'] == sent[0].id
        )
        assert stored['content'] == content
        assert stored['attachments'][0]['attachment_id'] == attachment.id

    def test_should_forward_attachment_references_to_message_submission(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, attempt, learner)
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            before = repositories.mentor_messages.find_all(
                MENTOR_ACCOUNT.account_id, session
            )

        ids = SystemIdentifierProvider()
        response = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages',
            json={
                'submission_key': '4b9e25c4-2a9b-42fe-9c37-649c844bc170',
                'content': 'Considere os arquivos enviados.',
                'attachment_batch_id': ids.generate(),
                'attachment_ids': [ids.generate()],
            },
        )

        assert response.status_code == 409
        assert response.headers['cache-control'] == 'private, no-store'
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            after = repositories.mentor_messages.find_all(
                MENTOR_ACCOUNT.account_id, session
            )
        assert after == before

    def test_should_persist_subsequent_text_and_replay_once(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, attempt, learner)
        payload = {
            'submission_key': '223e4567-e89b-42d3-a456-426614174000',
            'content': '  Texto exato\nsegunda mensagem  ',
            'context_hint': {
                'goal_id': '01J7T8AC91Z5K8M4JQ8C2D6F0D',
                'skill_id': None,
                'competency_id': None,
                'material_id': None,
                'activity_id': None,
            },
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
        accepted_body = accepted.json()
        assert set(accepted_body) == {
            'session',
            'messages',
            'pending_learner_message_id',
            'response',
        }
        response_snapshot = accepted_body['response']
        assert {
            'attempt_id',
            'learner_message_id',
            'status',
            'blocks',
            'consultations',
            'last_sequence',
            'failure_code',
        } <= set(response_snapshot)
        assert (
            replay.json()['response']['attempt_id'] == response_snapshot['attempt_id']
        )
        # The registered AgentOS worker may advance the attempt before the
        # request snapshot is serialized.
        assert response_snapshot['status'] in {
            'queued',
            'completed',
        }
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            messages = repositories.mentor_messages.find_all(
                MENTOR_ACCOUNT.account_id, session
            )
            current = repositories.mentor_response_attempts.find_current(
                MENTOR_ACCOUNT.account_id, session
            )
            response_events = repositories.mentor_response_events.find_after(
                MENTOR_ACCOUNT.account_id, session, 0
            )
            assert len(messages) == 3
            assert messages[-1].content == payload['content']
            assert current is not None
            assert current.id == response_snapshot['attempt_id']
            assert current.learner_message_id == response_snapshot['learner_message_id']
            assert messages[-1].id == current.learner_message_id
            assert current.context_hint is not None
            assert current.context_hint.goal_id == '01J7T8AC91Z5K8M4JQ8C2D6F0D'
            assert any(
                event.attempt_id == current.id
                and event.kind.value == 'status'
                and event.status.value == 'queued'
                for event in response_events
            )

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

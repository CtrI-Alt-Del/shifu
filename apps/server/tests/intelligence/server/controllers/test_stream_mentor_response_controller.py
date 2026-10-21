import json
from typing import cast, TYPE_CHECKING
from fastapi.testclient import TestClient

from shifu.intelligence.core.domain.enums import MentorWorkflowStep
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import configure_mentor_access
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    append_status,
    create_session,
    complete_response,
    start_processing,
)


if TYPE_CHECKING:
    from fastapi import FastAPI


class TestStreamMentorResponseController:
    def test_should_stream_ordered_approved_events_without_reinference(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, attempt, learner)
        response = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': '1'},
        )
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/event-stream')
        assert response.headers['cache-control'] == 'private, no-store'
        assert 'id:2\nevent:mentor.response\ndata:' in response.text
        assert 'Resposta sintética aprovada.' in response.text
        assert '"kind":"completed"' in response.text
        assert '"sequence":1,' not in response.text
        assert 'access_revision' not in response.text
        assert 'operation_key' not in response.text
        assert 'Bearer' not in response.text

    def test_should_replay_actual_workflow_steps_and_clear_terminal_snapshot(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(
            postgres_database,
            session,
            attempt,
            learner,
            progress=(
                MentorWorkflowStep.WRITE_ANSWER,
                MentorWorkflowStep.REVIEW_ANSWER,
                MentorWorkflowStep.WRITE_ANSWER,
                MentorWorkflowStep.REVIEW_ANSWER,
            ),
        )
        response = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': '1'},
        )
        assert response.status_code == 200
        events = [
            json.loads(line.removeprefix('data:'))
            for line in response.text.splitlines()
            if line.startswith('data:')
        ]
        assert [event['progress'] for event in events] == [
            'write-answer',
            'review-answer',
            'write-answer',
            'review-answer',
            None,
            None,
        ]
        assert [event['sequence'] for event in events] == [2, 3, 4, 5, 6, 7]
        assert all(
            event['kind'] == 'status' and event['block'] is None for event in events[:4]
        )
        assert all(event['consultation'] is None for event in events)
        replayed = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': '3'},
        )
        assert replayed.status_code == 200
        assert '"sequence":2,' not in replayed.text
        assert '"sequence":3,' not in replayed.text
        assert '"progress":"write-answer"' in replayed.text
        detail = mentor_client.get(f'/intelligence/mentor-sessions/{session}')
        assert detail.status_code == 200
        assert detail.json()['response']['status'] == 'completed'
        assert detail.json()['response']['progress'] is None

    def test_should_reject_malformed_negative_cursor_or_foreign_resource(
        self, mentor_client: TestClient
    ) -> None:
        session, _, _ = create_session(mentor_client)
        malformed = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': 'abc'},
        )
        negative = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': '-1'},
        )
        unknown = mentor_client.get(
            '/intelligence/mentor-sessions/00000000000000000000000000/events'
        )
        assert malformed.status_code == negative.status_code == 422
        assert unknown.status_code == 404
        assert 'text/event-stream' not in malformed.headers.get('content-type', '')

    def test_should_fail_closed_before_exposing_events_when_access_revoked(
        self, mentor_client: TestClient
    ) -> None:
        session, _, _ = create_session(mentor_client)
        access = configure_mentor_access(cast('FastAPI', mentor_client.app))
        access.assert_current.side_effect = ServiceUnavailableError()
        response = mentor_client.get(f'/intelligence/mentor-sessions/{session}/events')
        assert response.status_code == 503
        assert 'Pergunta inicial' not in response.text
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_heartbeat_when_caught_up_and_close_safely_when_next_poll_loses_access(
        self, mentor_client: TestClient
    ) -> None:
        session, _, _ = create_session(mentor_client)
        access = configure_mentor_access(cast('FastAPI', mentor_client.app))
        access.assert_current.side_effect = [None, None, ServiceUnavailableError()]
        response = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': '1'},
        )
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.text == ': heartbeat\n\n'
        assert access.assert_current.call_count == 3
        assert 'Pergunta inicial' not in response.text

    def test_should_resume_session_stream_after_prior_attempt_without_reusing_its_blocks(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, first_attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, first_attempt, learner)
        prior = mentor_client.get(f'/intelligence/mentor-sessions/{session}')
        assert prior.status_code == 200
        previous_sequence = prior.json()['response']['last_sequence']
        submitted = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/messages',
            json={
                'submission_key': '223e4567-e89b-42d3-a456-426614174000',
                'content': 'Uma nova pergunta independente.',
            },
        )
        assert submitted.status_code == 202
        second_attempt = submitted.json()['response']['attempt_id']
        assert second_attempt != first_attempt
        cancelled = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/responses/{second_attempt}/cancel',
            json={'submission_key': '323e4567-e89b-42d3-a456-426614174000'},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()['status'] == 'cancelled'
        assert cancelled.json()['blocks'] == []
        detail = mentor_client.get(f'/intelligence/mentor-sessions/{session}')
        assert detail.status_code == 200
        assert detail.json()['response']['attempt_id'] == second_attempt
        assert detail.json()['response']['blocks'] == []
        streamed = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': str(previous_sequence)},
        )
        assert streamed.status_code == 200
        assert streamed.headers['cache-control'] == 'private, no-store'
        events = [
            json.loads(line.removeprefix('data:'))
            for line in streamed.text.splitlines()
            if line.startswith('data:')
        ]
        assert len(events) == 2
        assert all(event['attempt_id'] == second_attempt for event in events)
        assert [event['sequence'] for event in events] == [
            previous_sequence + 1,
            previous_sequence + 2,
        ]
        assert [event['status'] for event in events] == ['queued', 'cancelled']
        assert all(event['block'] is None for event in events)
        assert 'Resposta sintética aprovada.' not in streamed.text


class TestStreamMentorResponseControllerSummaryProgress:
    def test_should_replay_summarize_context_then_the_closing_null_progress_event(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(
            postgres_database,
            session,
            attempt,
            learner,
            progress=(
                MentorWorkflowStep.SUMMARIZE_CONTEXT,
                None,
                MentorWorkflowStep.WRITE_ANSWER,
            ),
        )
        response = mentor_client.get(
            f'/intelligence/mentor-sessions/{session}/events',
            headers={'Last-Event-ID': '1'},
        )

        events = [
            json.loads(line.removeprefix('data:'))
            for line in response.text.splitlines()
            if line.startswith('data:')
        ]

        assert [event['progress'] for event in events[:3]] == [
            'summarize-context',
            None,
            'write-answer',
        ]
        assert all(event['kind'] == 'status' for event in events[:3])
        assert [event['sequence'] for event in events[:3]] == [2, 3, 4]

    def test_should_resume_after_the_summarize_event_and_clear_progress_in_the_snapshot(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, _ = create_session(mentor_client)
        start_processing(postgres_database, attempt)
        append_status(
            postgres_database, session, attempt, MentorWorkflowStep.SUMMARIZE_CONTEXT
        )
        path = f'/intelligence/mentor-sessions/{session}'
        assert mentor_client.get(path).json()['response']['progress'] == (
            'summarize-context'
        )
        append_status(postgres_database, session, attempt, None)
        snapshot = mentor_client.get(path).json()['response']

        assert snapshot['progress'] is None
        assert snapshot['last_sequence'] == 3

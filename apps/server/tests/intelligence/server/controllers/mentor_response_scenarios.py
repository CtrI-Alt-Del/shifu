from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

from fastapi.testclient import TestClient

from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseBlock,
    MentorResponseEvent,
)
from shifu.intelligence.core.use_cases import FinalizeMentorResponseUseCase
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT


def create_session(
    client: TestClient, submission_key: str = '123e4567-e89b-42d3-a456-426614174000'
) -> tuple[str, str, str]:
    response = client.post(
        '/intelligence/mentor-sessions',
        json={'submission_key': submission_key, 'first_message': 'Pergunta inicial'},
    )
    assert response.status_code == 201
    body = response.json()
    return (
        body['session']['id'],
        body['response']['attempt_id'],
        body['pending_learner_message_id'],
    )


def complete_response(
    database: PostgresDatabase,
    session_id: str,
    attempt_id: str,
    message_id: str,
    progress: tuple[MentorWorkflowStep, ...] = (),
) -> None:
    intelligence = SqlalchemyIntelligenceDatabase(database.engine)
    now = datetime.now(UTC)
    with intelligence.transaction() as repositories:
        attempt = repositories.mentor_response_attempts.find_by_id_for_update(
            attempt_id
        )
        assert attempt is not None
        assert repositories.mentor_response_attempts.claim(
            attempt_id,
            'test-owner',
            now,
            now + timedelta(minutes=5),
            attempt.access_revision,
        )
        assert repositories.mentor_response_attempts.transition(
            attempt_id,
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
            attempt.access_revision,
        )
        for step in progress:
            repositories.mentor_response_events.append(
                MentorResponseEvent(
                    session_id=session_id,
                    attempt_id=attempt_id,
                    sequence=repositories.mentor_response_events.next_sequence(
                        session_id
                    ),
                    kind=MentorResponseEventKind.STATUS,
                    status=MentorResponseStatus.PROCESSING,
                    block=None,
                    consultation=None,
                    failure_code=None,
                    created_at=now,
                    progress=step,
                )
            )
        block = MentorResponseBlock(
            block_key='synthetic-approved',
            ordinal=0,
            intent=None,
            content='Resposta sintética aprovada.',
        )
        repositories.mentor_response_events.append(
            MentorResponseEvent(
                session_id=session_id,
                attempt_id=attempt_id,
                sequence=repositories.mentor_response_events.next_sequence(session_id),
                kind=MentorResponseEventKind.BLOCK,
                status=MentorResponseStatus.PROCESSING,
                block=block,
                consultation=None,
                failure_code=None,
                created_at=now,
            )
        )
    access = create_autospec(MentorAccessProvider, instance=True)
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    assert FinalizeMentorResponseUseCase(
        intelligence, SystemIdentifierProvider(), clock, access
    ).execute(
        MENTOR_ACCOUNT.account_id,
        session_id,
        message_id,
        'Resposta sintética aprovada.',
        attempt_id,
        'test-owner',
    )

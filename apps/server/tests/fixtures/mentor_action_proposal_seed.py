"""Seed a Mentor action proposal with the conversation rows it depends on.

Job tests persist through the real Intelligence database of the disposable
PostgreSQL, so the foreign keys to the session, learner message and attempt hold.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import create_engine

from shifu.fakers.intelligence.entities import MentorActionProposalFaker
from shifu.intelligence.core.domain.entities import (
    MentorMessage,
    MentorResponseAttempt,
    MentorSession,
)
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.use_cases.mentor_detail import mentor_action_item
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase

if TYPE_CHECKING:
    from shifu.intelligence.core.domain.entities import MentorActionProposal
    from shifu.shared.providers.system_identifier_provider import (
        SystemIdentifierProvider,
    )
    from tests.fixtures.inngest_fixture import InngestFixture

_SEEDED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def seed_mentor_action_proposal(
    fixture: InngestFixture,
    ids: SystemIdentifierProvider,
    account_id: str,
    **changes: Any,
) -> MentorActionProposal:
    """Persist a conversation, its learner message and attempt, one proposal and its event.

    Keyword arguments override the faker defaults of the proposal (kind, status,
    destination, candidates...).
    """
    session_id, message_id, attempt_id = (ids.generate() for _ in range(3))
    proposal = MentorActionProposalFaker.fake(
        account_id=account_id,
        session_id=session_id,
        learner_message_id=message_id,
        attempt_id=attempt_id,
        created_at=_SEEDED_AT,
        **changes,
    )
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=account_id,
                    title='Conversa',
                    created_at=_SEEDED_AT,
                    updated_at=_SEEDED_AT,
                    last_activity_at=_SEEDED_AT,
                ),
                str(uuid4()),
                'fingerprint',
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=message_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Adicione Funções em Python ao meu Objetivo',
                    created_at=_SEEDED_AT,
                    in_reply_to_message_id=None,
                )
            )
            repositories.mentor_response_attempts.add(
                MentorResponseAttempt.create(
                    id=attempt_id,
                    account_id=account_id,
                    session_id=session_id,
                    learner_message_id=message_id,
                    status=MentorResponseStatus.COMPLETED,
                    context_hint=None,
                    access_revision='revision',
                    operation_key='operation',
                    created_at=_SEEDED_AT,
                    updated_at=_SEEDED_AT,
                )
            )
            repositories.mentor_action_proposals.add(proposal)
            repositories.mentor_response_events.append(
                MentorResponseEvent(
                    session_id=session_id,
                    attempt_id=attempt_id,
                    sequence=repositories.mentor_response_events.next_sequence(
                        session_id
                    ),
                    kind=MentorResponseEventKind.ACTION,
                    status=MentorResponseStatus.PROCESSING,
                    block=None,
                    consultation=None,
                    failure_code=None,
                    created_at=_SEEDED_AT,
                    action_proposal=mentor_action_item(proposal),
                )
            )
    finally:
        engine.dispose()
    return proposal

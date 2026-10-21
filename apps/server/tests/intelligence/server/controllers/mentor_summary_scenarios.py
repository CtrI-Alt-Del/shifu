from datetime import UTC, datetime, timedelta

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSessionSummary
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorSummaryExcerptKind,
    MentorSummaryFailureCode,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryDraft,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT

LEARNER_TEXT = 'Meu laço não mostra o último item da lista.'
MENTOR_TEXT = 'Veja quais índices range produz e compare com o tamanho da lista.'
FIRST_TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)


def seed_exchanges(
    database: PostgresDatabase, session_id: str, exchanges: int
) -> tuple[MentorMessage, ...]:
    """Persist answered learner/Mentor pairs with controlled, ordered timestamps."""
    intelligence = SqlalchemyIntelligenceDatabase(database.engine)
    identifiers = SystemIdentifierProvider()
    messages: list[MentorMessage] = []
    with intelligence.transaction() as repositories:
        for index in range(exchanges):
            learner = MentorMessage(
                id=identifiers.generate(),
                session_id=session_id,
                role=MentorMessageRole.LEARNER,
                content=LEARNER_TEXT if index == 0 else f'Pergunta {index}.',
                created_at=FIRST_TIMESTAMP + timedelta(minutes=index * 2),
                in_reply_to_message_id=None,
            )
            mentor = MentorMessage(
                id=identifiers.generate(),
                session_id=session_id,
                role=MentorMessageRole.MENTOR,
                content=MENTOR_TEXT if index == 0 else f'Resposta {index}.',
                created_at=FIRST_TIMESTAMP + timedelta(minutes=index * 2 + 1),
                in_reply_to_message_id=learner.id,
            )
            repositories.mentor_messages.add(learner)
            repositories.mentor_messages.add(mentor)
            messages.extend((learner, mentor))
    return tuple(messages)


def seed_summary(
    database: PostgresDatabase,
    session_id: str,
    attempt_id: str,
    messages: tuple[MentorMessage, ...],
    *,
    version: int = 1,
    failure: MentorSummaryFailureCode | None = None,
    account_id: str = MENTOR_ACCOUNT.account_id,
) -> MentorSessionSummary:
    """Persist a ready (or failed) summary whose boundary is the last given message."""
    last = messages[-1]
    started = MentorSessionSummary.start(
        id=SystemIdentifierProvider().generate(),
        account_id=account_id,
        session_id=session_id,
        attempt_id=attempt_id,
        version=version,
        boundary=MentorSummaryBoundary(message_id=last.id, created_at=last.created_at),
        covered_message_count=len(messages),
        first_message_id=messages[0].id,
        now=FIRST_TIMESTAMP + timedelta(days=1),
    )
    if failure is not None:
        summary = started.fail(failure, FIRST_TIMESTAMP + timedelta(days=1))
    else:
        summary = started.complete(
            MentorConversationSummaryDraft(
                topics=('range', 'lista'),
                excerpts=(
                    MentorSummaryExcerptSpan(
                        message_id=messages[0].id,
                        start=0,
                        end=len(LEARNER_TEXT),
                        kind=MentorSummaryExcerptKind.DOUBT,
                    ),
                    MentorSummaryExcerptSpan(
                        message_id=messages[1].id,
                        start=0,
                        end=len(MENTOR_TEXT),
                        kind=MentorSummaryExcerptKind.GUIDANCE,
                    ),
                ),
                algorithm_version='textrank-v1',
            ),
            FIRST_TIMESTAMP + timedelta(days=1),
        )
    with SqlalchemyIntelligenceDatabase(database.engine).transaction() as repositories:
        repositories.mentor_session_summaries.add(summary)
    return summary


def count_summaries(database: PostgresDatabase, session_id: str) -> int:
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from shifu.intelligence.database.sqlalchemy.models import (
        MentorSessionSummaryModel,
    )

    with Session(database.engine) as session:
        return (
            session.scalar(
                select(func.count()).where(
                    MentorSessionSummaryModel.session_id == session_id
                )
            )
            or 0
        )

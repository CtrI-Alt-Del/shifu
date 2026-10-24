from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import create_engine, func, select

from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    LearnerMemoryChange,
    MentorMessage,
    MentorSession,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    LearnerMemoryChangeKind,
    MentorMessageRole,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryConcept,
    LearnerMemoryOrigin,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import (
    LearnerMemoryChangeModel,
    LearnerMemoryConceptModel,
    LearnerMemoryFenceModel,
    LearnerMemoryModel,
    LearnerMemoryOriginModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

_DELETED_AT = datetime(2026, 1, 1, tzinfo=UTC)
_MODELS = (
    LearnerMemoryModel,
    LearnerMemoryOriginModel,
    LearnerMemoryConceptModel,
    LearnerMemoryChangeModel,
    LearnerMemoryFenceModel,
)


def _seed_memory_data(
    fixture: 'InngestFixture', ids: SystemIdentifierProvider, account_id: str
) -> str:
    """Persist a memory with origin, concept, change record and fence; return its id."""
    session_id, message_id, memory_id = (ids.generate() for _ in range(3))
    engine = create_engine(fixture.database_url, pool_pre_ping=True)
    try:
        database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=account_id,
                    title='Conversa',
                    created_at=_DELETED_AT,
                    updated_at=_DELETED_AT,
                    last_activity_at=_DELETED_AT,
                ),
                str(uuid4()),
                'fingerprint',
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=message_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Prefiro exemplos em Python.',
                    created_at=_DELETED_AT,
                    in_reply_to_message_id=None,
                )
            )
            repositories.learner_memories.lock_account(account_id)
            repositories.learner_memories.add(
                LearnerMemory(
                    id=memory_id,
                    account_id=account_id,
                    category=LearnerMemoryCategory.EXPLANATION_PREFERENCE,
                    content='Prefiro exemplos em Python.',
                    version=1,
                    last_declared_at=_DELETED_AT,
                    created_at=_DELETED_AT,
                    updated_at=_DELETED_AT,
                ),
                (LearnerMemoryConcept(key='python', label='Python'),),
                LearnerMemoryOrigin(
                    session_id=session_id,
                    message_id=message_id,
                    declared_at=_DELETED_AT,
                ),
            )
            repositories.learner_memory_changes.add(
                LearnerMemoryChange(
                    id=ids.generate(),
                    account_id=account_id,
                    memory_id=memory_id,
                    session_id=session_id,
                    message_id=message_id,
                    kind=LearnerMemoryChangeKind.CREATED,
                    category=LearnerMemoryCategory.EXPLANATION_PREFERENCE,
                    content='Prefiro exemplos em Python.',
                    previous_content=None,
                    created_at=_DELETED_AT,
                )
            )
            repositories.learner_memories.advance_fence(
                account_id, _DELETED_AT - timedelta(days=1)
            )
    finally:
        engine.dispose()
    return memory_id


def _row_counts(session: 'Session', account_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in (LearnerMemoryModel, LearnerMemoryChangeModel):
        counts[model.__tablename__] = (
            session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.account_id == account_id)
            )
            or 0
        )
    counts[LearnerMemoryFenceModel.__tablename__] = (
        session.scalar(
            select(func.count())
            .select_from(LearnerMemoryFenceModel)
            .where(LearnerMemoryFenceModel.account_id == account_id)
        )
        or 0
    )
    return counts


def _total_rows(session: 'Session') -> int:
    return sum(
        session.scalar(select(func.count()).select_from(model)) or 0
        for model in _MODELS
    )


def _publish_account_deleted(
    fixture: 'InngestFixture',
    ids: SystemIdentifierProvider,
    account_id: str,
    **extra: str,
) -> str:
    event = AccountDeletedEvent(
        payload=AccountDeletedPayload(
            account_id=account_id,
            deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
        )
    )
    event_id = ids.generate()
    fixture.publish(
        event.name,
        {
            'account_id': event.payload.account_id,
            'deleted_at': event.payload.deleted_at,
            **extra,
        },
        event_id=event_id,
    )
    return event_id


class TestPurgeLearnerMemoriesOnAccountDeletedJob:
    def test_should_purge_only_the_deleted_accounts_memory_data(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        _seed_memory_data(inngest_fixture, ids, account_id)
        other_memory_id = _seed_memory_data(inngest_fixture, ids, other_account_id)
        with inngest_fixture.inspection_session() as session:
            assert _row_counts(session, account_id) == {
                'intelligence_learner_memories': 1,
                'intelligence_learner_memory_changes': 1,
                'intelligence_learner_memory_fences': 1,
            }

        _publish_account_deleted(inngest_fixture, ids, account_id)

        inngest_fixture.wait_for_database(
            lambda session: all(
                count == 0 for count in _row_counts(session, account_id).values()
            )
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(LearnerMemoryModel, other_memory_id) is not None
            assert _row_counts(session, other_account_id) == {
                'intelligence_learner_memories': 1,
                'intelligence_learner_memory_changes': 1,
                'intelligence_learner_memory_fences': 1,
            }
            origins = session.scalar(
                select(func.count()).select_from(LearnerMemoryOriginModel)
            )
            concepts = session.scalar(
                select(func.count()).select_from(LearnerMemoryConceptModel)
            )
            assert (origins, concepts) == (1, 1)

    def test_should_succeed_without_effect_on_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        _seed_memory_data(inngest_fixture, ids, account_id)
        _seed_memory_data(inngest_fixture, ids, other_account_id)

        _publish_account_deleted(inngest_fixture, ids, account_id)
        inngest_fixture.wait_for_database(
            lambda session: all(
                count == 0 for count in _row_counts(session, account_id).values()
            )
        )
        _publish_account_deleted(inngest_fixture, ids, account_id)
        # Deliveries are handled in order, so the other account's purge proves the
        # duplicate for the first account completed without a failure.
        _publish_account_deleted(inngest_fixture, ids, other_account_id)
        inngest_fixture.wait_for_database(lambda session: _total_rows(session) == 0)

    def test_should_reject_invalid_payloads_as_non_retriable_without_purging(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        memory_id = _seed_memory_data(inngest_fixture, ids, account_id)

        event_id = _publish_account_deleted(
            inngest_fixture, ids, account_id, unexpected='must be rejected'
        )

        inngest_fixture.wait_for_log(
            f'learner_memory_account_deletion_payload_rejected event_id={event_id}'
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(LearnerMemoryModel, memory_id) is not None
            assert _row_counts(session, account_id) == {
                'intelligence_learner_memories': 1,
                'intelligence_learner_memory_changes': 1,
                'intelligence_learner_memory_fences': 1,
            }

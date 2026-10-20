from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import create_engine

from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.intelligence.core.domain.entities import (
    MentorAttachmentBatch,
    MentorMessage,
    MentorSession,
    MentorSessionSummary,
)
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorSummaryExcerptKind,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryDraft,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import (
    MentorAttachmentBatchModel,
    MentorSessionSummaryModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture

_DELETED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _seed_summary(
    fixture: 'InngestFixture', ids: SystemIdentifierProvider, account_id: str
) -> str:
    """Persist a conversation with a ready summary and return the summary id."""
    session_id, learner_id, mentor_id, summary_id = (ids.generate() for _ in range(4))
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
                    id=learner_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Como funciona o range?',
                    created_at=_DELETED_AT,
                    in_reply_to_message_id=None,
                )
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=mentor_id,
                    session_id=session_id,
                    role=MentorMessageRole.MENTOR,
                    content='O range produz uma sequência de números.',
                    created_at=_DELETED_AT + timedelta(seconds=1),
                    in_reply_to_message_id=learner_id,
                )
            )
            started = MentorSessionSummary.start(
                id=summary_id,
                account_id=account_id,
                session_id=session_id,
                attempt_id=ids.generate(),
                version=1,
                boundary=MentorSummaryBoundary(
                    message_id=mentor_id,
                    created_at=_DELETED_AT + timedelta(seconds=1),
                ),
                covered_message_count=2,
                first_message_id=learner_id,
                now=_DELETED_AT,
            )
            # The attempt row does not exist here; a ready row does not need it.
            repositories.mentor_session_summaries.add(
                replace(
                    started.complete(
                        MentorConversationSummaryDraft(
                            topics=('range',),
                            excerpts=(
                                MentorSummaryExcerptSpan(
                                    message_id=learner_id,
                                    start=0,
                                    end=5,
                                    kind=MentorSummaryExcerptKind.DOUBT,
                                ),
                            ),
                            algorithm_version='textrank-v1',
                        ),
                        _DELETED_AT,
                    ),
                    attempt_id=None,
                )
            )
    finally:
        engine.dispose()
    return summary_id


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


class TestPurgeMentorSummariesOnAccountDeletedJob:
    def test_should_purge_only_the_deleted_accounts_summaries_and_still_run_the_attachment_purge(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        summary_id = _seed_summary(inngest_fixture, ids, account_id)
        other_summary_id = _seed_summary(inngest_fixture, ids, other_account_id)
        batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            with SqlalchemyIntelligenceDatabase(
                engine, id_provider=ids
            ).transaction() as repositories:
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        batch_id,
                        account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
        finally:
            engine.dispose()

        _publish_account_deleted(inngest_fixture, ids, account_id)

        inngest_fixture.wait_for_database(
            lambda session: (
                session.get(MentorSessionSummaryModel, summary_id) is None
                and session.get(MentorAttachmentBatchModel, batch_id) is None
            )
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorSessionSummaryModel, other_summary_id) is not None

    def test_should_succeed_without_effect_on_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        summary_id = _seed_summary(inngest_fixture, ids, account_id)
        other_summary_id = _seed_summary(inngest_fixture, ids, other_account_id)

        _publish_account_deleted(inngest_fixture, ids, account_id)
        inngest_fixture.wait_for_database(
            lambda session: session.get(MentorSessionSummaryModel, summary_id) is None
        )
        _publish_account_deleted(inngest_fixture, ids, account_id)
        # The second delivery of the same account must not touch other accounts.
        _publish_account_deleted(inngest_fixture, ids, other_account_id)
        inngest_fixture.wait_for_database(
            lambda session: (
                session.get(MentorSessionSummaryModel, other_summary_id) is None
            )
        )

        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorSessionSummaryModel, summary_id) is None

    def test_should_reject_invalid_payloads_as_non_retriable_without_purging(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        summary_id = _seed_summary(inngest_fixture, ids, account_id)

        event_id = _publish_account_deleted(
            inngest_fixture, ids, account_id, unexpected='must be rejected'
        )

        inngest_fixture.wait_for_log(
            f'mentor_summary_account_deletion_payload_rejected event_id={event_id}'
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorSessionSummaryModel, summary_id) is not None

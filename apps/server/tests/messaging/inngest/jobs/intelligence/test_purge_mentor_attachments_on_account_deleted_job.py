from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine

from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.intelligence.core.domain.entities import MentorAttachmentBatch
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import MentorAttachmentBatchModel
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture

_DELETED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class TestPurgeMentorAttachmentsOnAccountDeletedJob:
    def test_should_purge_account_batches_after_retention_period(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        batch_id = ids.generate()
        other_account_id = ids.generate()
        other_batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        batch_id,
                        account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
                repositories.mentor_attachment_batches.add(
                    MentorAttachmentBatch.create(
                        other_batch_id,
                        other_account_id,
                        None,
                        _DELETED_AT,
                        _DELETED_AT + timedelta(hours=1),
                    )
                )
        finally:
            engine.dispose()

        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
            )
        )
        event_id = ids.generate()
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_database(
            lambda session: (
                session.get(MentorAttachmentBatchModel, batch_id) is None
                and session.get(MentorAttachmentBatchModel, other_batch_id) is not None
            )
        )

    def test_should_reject_extra_account_deleted_payload_fields_without_purging(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
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

        event = AccountDeletedEvent(
            payload=AccountDeletedPayload(
                account_id=account_id,
                deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
            )
        )
        event_id = ids.generate()
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
                'unexpected': 'must be rejected',
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_log(
            f'mentor_attachment_account_deletion_payload_rejected event_id={event_id}'
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorAttachmentBatchModel, batch_id) is not None

    @pytest.mark.parametrize(
        ('invalid_account_id', 'invalid_deleted_at'),
        [
            (' \t', _DELETED_AT.isoformat().replace('+00:00', 'Z')),
            (None, '2026-01-01T00:00:00'),
            (None, 'not-a-timestamp'),
        ],
    )
    def test_should_reject_invalid_canonical_payload_fields_without_purging(
        self,
        inngest_fixture: 'InngestFixture',
        invalid_account_id: str | None,
        invalid_deleted_at: str,
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        batch_id = ids.generate()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database = SqlalchemyIntelligenceDatabase(engine, id_provider=ids)
            with database.transaction() as repositories:
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

        payload = AccountDeletedPayload(
            account_id=invalid_account_id or account_id,
            deleted_at=invalid_deleted_at,
        )
        if invalid_account_id is not None:
            payload = AccountDeletedPayload(
                account_id=invalid_account_id,
                deleted_at=invalid_deleted_at,
            )
        event = AccountDeletedEvent(payload=payload)
        event_id = ids.generate()
        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'deleted_at': event.payload.deleted_at,
            },
            event_id=event_id,
        )

        inngest_fixture.wait_for_log(
            f'mentor_attachment_account_deletion_payload_rejected event_id={event_id}'
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorAttachmentBatchModel, batch_id) is not None

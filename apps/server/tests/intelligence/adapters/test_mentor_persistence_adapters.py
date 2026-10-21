from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
    MentorMessage,
    MentorResponseAttempt,
    MentorSession,
)
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorMessageRole,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
    MentorInferenceUsage,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.mappers import MentorSessionMapper
from shifu.intelligence.database.sqlalchemy.models import MentorSessionModel
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase


def _create_attachment(
    attachment_id: str,
    account_id: str,
    batch_id: str,
    created_at: datetime,
) -> MentorAttachment:
    return MentorAttachment.create(
        attachment_id=attachment_id,
        account_id=account_id,
        batch_id=batch_id,
        upload_key=str(uuid4()),
        filename='notes.txt',
        media_type='text/plain',
        size_bytes=12,
        checksum=sha256(attachment_id.encode()).hexdigest(),
        object_key=f'intelligence/{attachment_id}',
        now=created_at,
    )


def _mark_attachment_ready(attachment: MentorAttachment) -> None:
    attachment.apply_extraction(
        MentorAttachmentExtraction(
            chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
        ),
        MentorAttachmentStatus.READY,
    )


class TestMentorPersistenceAdapters:
    def test_should_reject_mapping_a_tombstoned_session(self) -> None:
        deleted_at = datetime.now(UTC)
        tombstone = MentorSessionModel(
            id='01J7T8AC91Z5K8M4JQ8C2D6F0B',
            account_id='01J7T8AC91Z5K8M4JQ8C2D6F0C',
            submission_key='a1d61118-477e-49e9-8f67-4b9f01045083',
            content_fingerprint=None,
            title=None,
            title_search=None,
            created_at=None,
            updated_at=None,
            last_activity_at=None,
            deleted_at=deleted_at,
        )

        with pytest.raises(
            ValueError, match='A deleted Mentor session cannot be mapped as active'
        ):
            MentorSessionMapper.to_domain(tombstone)

    def test_should_find_learner_message_and_its_response(
        self, postgres_database: PostgresDatabase
    ) -> None:
        identifiers = SystemIdentifierProvider()
        account_id = identifiers.generate()
        session_id = identifiers.generate()
        learner_message_id = identifiers.generate()
        response_id = identifiers.generate()
        timestamp = datetime.now(UTC)
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)

        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=account_id,
                    title='Conversa de persistência',
                    created_at=timestamp,
                    updated_at=timestamp,
                    last_activity_at=timestamp,
                ),
                str(uuid4()),
                sha256(b'first message').hexdigest(),
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=learner_message_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Primeira pergunta.',
                    created_at=timestamp,
                    in_reply_to_message_id=None,
                )
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=response_id,
                    session_id=session_id,
                    role=MentorMessageRole.MENTOR,
                    content='Resposta persistida.',
                    created_at=timestamp,
                    in_reply_to_message_id=learner_message_id,
                )
            )

            learner_message = repositories.mentor_messages.find_by_id(
                account_id, session_id, learner_message_id
            )
            response = repositories.mentor_messages.find_response(
                account_id, session_id, learner_message_id
            )

        assert learner_message is not None
        assert learner_message.content == 'Primeira pergunta.'
        assert response is not None
        assert response.id == response_id
        assert response.in_reply_to_message_id == learner_message_id

    def test_should_search_rename_and_redact_a_session_without_crossing_accounts(
        self, postgres_database: PostgresDatabase
    ) -> None:
        identifiers = SystemIdentifierProvider()
        account_id = identifiers.generate()
        other_account_id = identifiers.generate()
        session_id = identifiers.generate()
        timestamp = datetime.now(UTC)
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        session = MentorSession(
            id=session_id,
            account_id=account_id,
            title='Conversação em português',
            created_at=timestamp,
            updated_at=timestamp,
            last_activity_at=timestamp,
        )

        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                session,
                str(uuid4()),
                sha256(b'session body').hexdigest(),
            )
            assert (
                repositories.mentor_sessions.find_by_id(other_account_id, session_id)
                is None
            )
            page = repositories.mentor_sessions.find_many(
                account_id, 'conversacao', None
            )
            assert [item.id for item in page.items] == [session_id]
            assert page.next_cursor is None

            session.title = 'Revisão de listas'
            session.updated_at = datetime.now(UTC)
            repositories.mentor_sessions.rename(session)
            renamed = repositories.mentor_sessions.find_by_id(account_id, session_id)
            assert renamed is not None
            assert renamed.title == 'Revisão de listas'
            assert (
                repositories.mentor_sessions.find_many(
                    account_id, 'conversacao', None
                ).items
                == []
            )

            repositories.mentor_sessions.remove(session, datetime.now(UTC))
            assert (
                repositories.mentor_sessions.find_by_id(account_id, session_id) is None
            )
            assert (
                repositories.mentor_sessions.find_many(account_id, None, None).items
                == []
            )

    def test_should_persist_attachment_batches_attachments_and_eligible_chunks(
        self, postgres_database: PostgresDatabase
    ) -> None:
        identifiers = SystemIdentifierProvider()
        account_id = identifiers.generate()
        session_id = identifiers.generate()
        message_id = identifiers.generate()
        now = datetime(2026, 10, 1, tzinfo=UTC)
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        expired_batch = MentorAttachmentBatch.create(
            identifiers.generate(),
            account_id,
            session_id,
            now - timedelta(days=2),
            now - timedelta(days=1),
        )
        consumed_batch = MentorAttachmentBatch.create(
            identifiers.generate(),
            account_id,
            session_id,
            now - timedelta(days=2),
            now - timedelta(days=1),
        )
        consumed_batch.consume(identifiers.generate())
        scoped_batch = MentorAttachmentBatch.create(
            identifiers.generate(),
            account_id,
            session_id,
            now,
            now + timedelta(hours=1),
        )
        removable_batch = MentorAttachmentBatch.create(
            identifiers.generate(),
            account_id,
            None,
            now,
            now + timedelta(hours=1),
        )

        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=account_id,
                    title='Anexos persistidos',
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                ),
                str(uuid4()),
                sha256(b'initial message').hexdigest(),
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=message_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Leia este arquivo.',
                    created_at=now,
                    in_reply_to_message_id=None,
                )
            )
            for batch in (
                expired_batch,
                consumed_batch,
                scoped_batch,
                removable_batch,
            ):
                repositories.mentor_attachment_batches.add(batch)

            assert (
                repositories.mentor_attachment_batches.find_by_id(
                    expired_batch.id, for_update=True
                )
                == expired_batch
            )
            assert repositories.mentor_attachment_batches.find_by_id('missing') is None
            assert repositories.mentor_attachment_batches.find_by_account_id(
                account_id
            ) == tuple(
                sorted(
                    (expired_batch, consumed_batch, scoped_batch, removable_batch),
                    key=lambda batch: batch.id,
                )
            )
            assert repositories.mentor_attachment_batches.find_by_session_id(
                account_id, session_id
            ) == tuple(
                sorted(
                    (expired_batch, consumed_batch, scoped_batch),
                    key=lambda batch: batch.id,
                )
            )
            assert repositories.mentor_attachment_batches.find_expired(now, 1) == (
                expired_batch,
            )

            expired_batch.renew(now + timedelta(days=1))
            repositories.mentor_attachment_batches.update(expired_batch)
            assert repositories.mentor_attachment_batches.find_expired(now, 10) == ()
            repositories.mentor_attachment_batches.remove(removable_batch.id)
            assert (
                repositories.mentor_attachment_batches.find_by_id(removable_batch.id)
                is None
            )

            stale_upload = _create_attachment(
                identifiers.generate(),
                account_id,
                scoped_batch.id,
                now - timedelta(minutes=6),
            )
            expired_claim = _create_attachment(
                identifiers.generate(),
                account_id,
                scoped_batch.id,
                now - timedelta(minutes=10),
            )
            expired_claim.claim(
                'expired-worker',
                now - timedelta(minutes=10),
                now - timedelta(minutes=1),
            )
            recent_upload = _create_attachment(
                identifiers.generate(), account_id, scoped_batch.id, now
            )
            live_claim = _create_attachment(
                identifiers.generate(),
                account_id,
                scoped_batch.id,
                now - timedelta(minutes=10),
            )
            live_claim.claim('live-worker', now, now + timedelta(minutes=1))
            ready = _create_attachment(
                identifiers.generate(),
                account_id,
                scoped_batch.id,
                now - timedelta(minutes=2),
            )
            _mark_attachment_ready(ready)
            ready.bind(session_id, message_id)
            removed = _create_attachment(
                identifiers.generate(),
                account_id,
                scoped_batch.id,
                now - timedelta(minutes=2),
            )
            _mark_attachment_ready(removed)
            removed.bind(session_id, message_id)
            removed.transition(MentorAttachmentStatus.REMOVED)
            attachments = (
                stale_upload,
                expired_claim,
                recent_upload,
                live_claim,
                ready,
                removed,
            )
            for attachment in attachments:
                repositories.mentor_attachments.add(attachment)

            assert (
                repositories.mentor_attachments.find_by_id(ready.id, for_update=True)
                == ready
            )
            assert repositories.mentor_attachments.find_by_id('missing') is None
            assert (
                repositories.mentor_attachments.find_by_upload_key(
                    scoped_batch.id, ready.upload_key
                )
                == ready
            )
            assert (
                repositories.mentor_attachments.find_by_upload_key(
                    scoped_batch.id, 'unknown-upload-key'
                )
                is None
            )
            assert repositories.mentor_attachments.find_by_batch_id(
                scoped_batch.id
            ) == tuple(sorted(attachments, key=lambda item: (item.created_at, item.id)))
            assert repositories.mentor_attachments.find_by_message_id(message_id) == (
                ready,
            )
            assert {
                attachment.id
                for attachment in repositories.mentor_attachments.find_by_session_id(
                    account_id, session_id
                )
            } == {attachment.id for attachment in attachments}
            assert repositories.mentor_attachments.find_for_cleanup(
                account_id, session_id, None
            ) == (removed,)
            assert {
                attachment.id
                for attachment in repositories.mentor_attachments.find_for_cleanup(
                    account_id, None, scoped_batch.id, removed_only=False
                )
            } == {attachment.id for attachment in attachments}
            assert {
                attachment.id
                for attachment in repositories.mentor_attachments.find_for_cleanup(
                    account_id, None, None, removed_only=False
                )
            } == {attachment.id for attachment in attachments}
            assert (
                repositories.mentor_attachments.count_active_in_batch(scoped_batch.id)
                == len(attachments) - 1
            )
            assert repositories.mentor_attachments.find_expired_reservations(
                now, 10
            ) == (
                expired_claim,
                stale_upload,
            )

            ready_chunks = (
                MentorAttachmentChunk(
                    chunk_id=identifiers.generate(),
                    attachment_id=ready.id,
                    generation=ready.generation,
                    page_number=1,
                    locator='chars:20-30#1',
                    content='Trecho B',
                ),
                MentorAttachmentChunk(
                    chunk_id=identifiers.generate(),
                    attachment_id=ready.id,
                    generation=ready.generation,
                    page_number=1,
                    locator='chars:1-10#1',
                    content='Trecho A',
                ),
                MentorAttachmentChunk(
                    chunk_id=identifiers.generate(),
                    attachment_id=ready.id,
                    generation=ready.generation,
                    page_number=2,
                    locator='page:2/chars:1-10#1',
                    content='Trecho C',
                ),
            )
            removed_chunk = MentorAttachmentChunk(
                chunk_id=identifiers.generate(),
                attachment_id=removed.id,
                generation=removed.generation,
                page_number=1,
                locator='chars:1-10#1',
                content='Removed content',
            )
            repositories.mentor_attachment_chunks.add_many(())
            repositories.mentor_attachment_chunks.add_many(
                (*ready_chunks, removed_chunk)
            )

            ordered_chunks = tuple(
                sorted(
                    ready_chunks, key=lambda chunk: (chunk.page_number, chunk.locator)
                )
            )
            assert (
                repositories.mentor_attachment_chunks.find_by_attachment_id(
                    ready.id, ready.generation
                )
                == ordered_chunks
            )
            assert (
                repositories.mentor_attachment_chunks.find_many_eligible(
                    account_id, session_id, (), ()
                )
                == ()
            )
            assert (
                repositories.mentor_attachment_chunks.find_many_eligible(
                    account_id, session_id, (ready.id,), ()
                )
                == ordered_chunks
            )
            assert repositories.mentor_attachment_chunks.find_many_eligible(
                account_id, session_id, (ready.id,), (2,)
            ) == (ordered_chunks[-1],)

            recent_upload.transition(MentorAttachmentStatus.FAILED, 'test-failure')
            repositories.mentor_attachments.update(recent_upload)
            assert (
                repositories.mentor_attachments.find_by_id(recent_upload.id)
                == recent_upload
            )
            repositories.mentor_attachments.remove('missing')
            repositories.mentor_attachments.remove(removed.id)
            assert repositories.mentor_attachments.find_by_id(removed.id) is None
            repositories.mentor_attachment_chunks.remove_by_attachment_id(ready.id)
            assert (
                repositories.mentor_attachment_chunks.find_by_attachment_id(
                    ready.id, ready.generation
                )
                == ()
            )

    def test_should_persist_response_attempt_claim_usage_and_submission_paths(
        self, postgres_database: PostgresDatabase
    ) -> None:
        identifiers = SystemIdentifierProvider()
        account_id = identifiers.generate()
        session_id = identifiers.generate()
        message_id = identifiers.generate()
        attempt_id = identifiers.generate()
        now = datetime(2026, 10, 1, tzinfo=UTC)
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        attempt = MentorResponseAttempt.create(
            id=attempt_id,
            account_id=account_id,
            session_id=session_id,
            learner_message_id=message_id,
            status=MentorResponseStatus.PROCESSING,
            context_hint=None,
            access_revision='revision-1',
            operation_key='operation-1',
            created_at=now,
            updated_at=now,
        )
        initial_usage = MentorInferenceUsage(
            call_key='call-1',
            profile='answer',
            used_tokens=24,
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
        )

        with database.transaction() as repositories:
            repositories.mentor_sessions.add(
                MentorSession(
                    id=session_id,
                    account_id=account_id,
                    title='Resposta persistida',
                    created_at=now,
                    updated_at=now,
                    last_activity_at=now,
                ),
                str(uuid4()),
                sha256(b'question').hexdigest(),
            )
            repositories.mentor_messages.add(
                MentorMessage(
                    id=message_id,
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content='Pergunta persistida.',
                    created_at=now,
                    in_reply_to_message_id=None,
                )
            )
            repositories.mentor_response_attempts.add(attempt)
            repositories.mentor_response_attempts.add_submission(
                account_id,
                session_id,
                'attempt-submission-key',
                attempt_id,
                'submission-fingerprint',
            )

            assert (
                repositories.mentor_response_attempts.find_by_id(attempt_id) == attempt
            )
            assert (
                repositories.mentor_response_attempts.find_by_id_for_update(attempt_id)
                == attempt
            )
            assert repositories.mentor_response_attempts.find_by_id('missing') is None
            assert (
                repositories.mentor_response_attempts.find_current(
                    account_id, session_id
                )
                == attempt
            )
            assert repositories.mentor_response_attempts.find_submission(
                account_id, session_id, 'attempt-submission-key'
            ) == (attempt, 'submission-fingerprint')
            assert (
                repositories.mentor_response_attempts.find_submission(
                    account_id, session_id, 'missing'
                )
                is None
            )
            assert (
                repositories.mentor_response_attempts.find_continuity(
                    account_id, session_id
                )
                == ()
            )

            assert repositories.mentor_response_attempts.inference_started('missing')
            assert not repositories.mentor_response_attempts.inference_started(
                attempt_id
            )
            assert repositories.mentor_response_attempts.claim(
                attempt_id,
                'worker-1',
                now,
                now + timedelta(minutes=1),
                'revision-1',
            )
            assert not repositories.mentor_response_attempts.claim(
                attempt_id,
                'worker-2',
                now,
                now + timedelta(minutes=1),
                'revision-1',
            )
            assert repositories.mentor_response_attempts.has_claim(
                attempt_id, 'worker-1', now
            )
            assert not repositories.mentor_response_attempts.has_claim(
                attempt_id, 'worker-1', now + timedelta(minutes=2)
            )
            assert not repositories.mentor_response_attempts.renew_claim(
                attempt_id,
                'worker-2',
                now,
                now + timedelta(minutes=3),
                'revision-1',
            )
            assert repositories.mentor_response_attempts.renew_claim(
                attempt_id,
                'worker-1',
                now,
                now + timedelta(minutes=3),
                'revision-1',
            )
            assert repositories.mentor_response_attempts.journal_usage(
                attempt_id, 'worker-1', 'revision-1', initial_usage
            )
            assert repositories.mentor_response_attempts.journal_usage(
                attempt_id, 'worker-1', 'revision-1', initial_usage
            )
            completed_usage = MentorInferenceUsage(
                call_key='call-1',
                profile='answer',
                used_tokens=24,
                input_tokens=19,
                output_tokens=5,
                cost_usd=0.001,
            )
            assert repositories.mentor_response_attempts.journal_usage(
                attempt_id, 'worker-1', 'revision-1', completed_usage
            )
            assert repositories.mentor_response_attempts.read_usage(attempt_id) == (
                completed_usage,
            )
            assert repositories.mentor_response_attempts.read_usage('missing') is None
            with pytest.raises(ServiceUnavailableError):
                repositories.mentor_response_attempts.journal_usage(
                    attempt_id,
                    'worker-1',
                    'revision-1',
                    MentorInferenceUsage(
                        call_key='call-1',
                        profile='different-profile',
                        used_tokens=24,
                        input_tokens=19,
                        output_tokens=5,
                        cost_usd=0.001,
                    ),
                )

            repositories.mentor_response_attempts.release_claim(attempt_id, 'wrong')
            repositories.mentor_response_attempts.release_claim(attempt_id, 'worker-1')
            assert not repositories.mentor_response_attempts.has_claim(
                attempt_id, 'worker-1', now
            )

            assert repositories.mentor_response_attempts.update_references(
                attempt_id, ('source-1',), 'revision-1'
            )
            assert not repositories.mentor_response_attempts.update_references(
                'missing', (), 'revision-1'
            )
            assert repositories.mentor_response_attempts.reserve_generation(
                attempt_id, 'block-1', 'revision-1'
            )
            assert not repositories.mentor_response_attempts.reserve_generation(
                attempt_id, 'block-1', 'revision-1'
            )
            assert repositories.mentor_response_attempts.inference_started(attempt_id)
            assert not repositories.mentor_response_attempts.reserve_generation(
                attempt_id, 'block-2', 'wrong-revision'
            )
            assert repositories.mentor_response_attempts.transition(
                attempt_id,
                MentorResponseStatus.PROCESSING,
                MentorResponseStatus.COMPLETED,
                'revision-1',
            )
            assert not repositories.mentor_response_attempts.transition(
                attempt_id,
                MentorResponseStatus.PROCESSING,
                MentorResponseStatus.FAILED,
                'revision-1',
            )
            assert repositories.mentor_response_attempts.find_continuity(
                account_id, session_id
            ) == ('source-1',)

            repositories.mentor_response_attempts.remove_by_session_id(session_id)
            assert repositories.mentor_response_attempts.find_by_id(attempt_id) is None

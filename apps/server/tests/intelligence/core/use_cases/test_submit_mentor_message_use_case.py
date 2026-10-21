from datetime import timedelta
from unittest.mock import call

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorAttachment,
    MentorAttachmentBatch,
)
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorMessageRole,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentConflictError,
    MentorInputInvalidError,
    MentorResponseConflictError,
    MentorSessionNotFoundError,
    MentorSubmissionConflictError,
)
from shifu.intelligence.core.domain.structures import (
    MentorContextHint,
    MentorSubmission,
)
from shifu.intelligence.core.domain.structures.mentor_submission_fingerprint import (
    mentor_submission_fingerprint,
    mentor_submission_fingerprint_v2,
)
from shifu.intelligence.core.use_cases import SubmitMentorMessageUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)


class TestSubmitMentorMessageUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare()
        self.subject = SubmitMentorMessageUseCase(
            self.database, self.identifiers, self.clock, self.access
        )

    def test_should_persist_exact_text_hint_attempt_and_outbox(self) -> None:
        hint = MentorContextHint(goal_id='goal', skill_id='skill')
        self.subject.execute(
            'account',
            'session',
            MentorSubmission(
                submission_key=self.key, content='  texto\nexato  ', context_hint=hint
            ),
        )
        message = self.repositories.mentor_messages.add.call_args.args[0]
        attempt = self.repositories.mentor_response_attempts.add.call_args.args[0]
        assert message.content == '  texto\nexato  '
        assert attempt.context_hint == hint
        assert attempt.learner_message_id == message.id
        assert attempt.access_revision == 'revision'
        event = self.repositories.events.add.call_args.args[0]
        assert event.name == 'intelligence/mentor.response.requested'
        assert event.payload.attempt_id == attempt.id
        self.access.authorize.assert_called_once_with('account', self.key)
        assert self.subject.replayed is False

    def test_should_replay_without_duplicate_writes(self) -> None:
        submission = MentorSubmission(submission_key=self.key, content='texto')
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            mentor_submission_fingerprint('texto', None),
        )
        self.subject.execute('account', 'session', submission)
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        assert self.subject.replayed is True

    def test_should_conflict_on_changed_hint_or_text(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            mentor_submission_fingerprint('texto', None),
        )
        with pytest.raises(MentorSubmissionConflictError):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(
                    submission_key=self.key,
                    content='texto',
                    context_hint=MentorContextHint(goal_id='other'),
                ),
            )
        self.repositories.events.add.assert_not_called()

    def test_should_reject_distinct_submit_while_learner_pending(self) -> None:
        self.repositories.mentor_messages.find_pending_learner_message_id.return_value = 'pending'
        with pytest.raises(MentorResponseConflictError):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(submission_key=self.key, content='texto'),
            )
        self.access.authorize.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_hide_foreign_session_without_authorizing(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute(
                'account',
                'foreign',
                MentorSubmission(submission_key=self.key, content='texto'),
            )
        self.access.authorize.assert_not_called()

    def test_should_fail_closed_without_entitlement(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(submission_key=self.key, content='texto'),
            )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize(
        ('key', 'text'),
        [
            ('bad', 'text'),
            ('123e4567-e89b-12d3-a456-426614174000', 'text'),
            ('123E4567-E89B-12D3-A456-426614174000', 'text'),
            ('123e4567-e89b-42d3-a456-426614174000', '  '),
        ],
    )
    def test_should_reject_invalid_input_without_transaction(
        self, key: str, text: str
    ) -> None:
        with pytest.raises(MentorInputInvalidError):
            self.subject.execute(
                'account', 'session', MentorSubmission(submission_key=key, content=text)
            )
        self.database.transaction.assert_not_called()

    def test_should_link_owned_submission_to_queued_stream_and_current_detail(
        self,
    ) -> None:
        self.repositories.mentor_messages.find_pending_learner_message_id.side_effect = [
            None,
            'message-new',
        ]
        self.session.updated_at = self.now - timedelta(days=1)
        self.session.last_activity_at = self.now - timedelta(days=1)
        submission = MentorSubmission(submission_key=self.key, content='texto')
        result = self.subject.execute('account', 'session', submission)
        message = self.repositories.mentor_messages.add.call_args.args[0]
        attempt = self.repositories.mentor_response_attempts.add.call_args.args[0]
        assert (
            message.session_id,
            message.role,
            message.created_at,
            message.in_reply_to_message_id,
        ) == ('session', MentorMessageRole.LEARNER, self.now, None)
        assert (
            attempt.account_id,
            attempt.session_id,
            attempt.status,
            attempt.operation_key,
            attempt.created_at,
            attempt.updated_at,
        ) == (
            'account',
            'session',
            MentorResponseStatus.QUEUED,
            'operation',
            self.now,
            self.now,
        )
        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.find_submission.assert_called_once_with(
            'account', 'session', self.key
        )
        self.repositories.mentor_response_attempts.add_submission.assert_called_once_with(
            'account',
            'session',
            self.key,
            attempt.id,
            mentor_submission_fingerprint_v2('texto', None, ()),
        )
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )
        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert (
            event.session_id,
            event.attempt_id,
            event.sequence,
            event.kind,
            event.status,
            event.created_at,
        ) == (
            'session',
            attempt.id,
            2,
            MentorResponseEventKind.STATUS,
            MentorResponseStatus.QUEUED,
            self.now,
        )
        assert (event.block, event.consultation, event.failure_code) == (
            None,
            None,
            None,
        )
        self.repositories.mentor_response_events.next_sequence.assert_called_once_with(
            'session'
        )
        self.repositories.mentor_messages.find_many.assert_called_once_with(
            'account', 'session', None
        )
        self.repositories.mentor_messages.find_pending_learner_message_id.assert_called_with(
            'account', 'session'
        )
        self.repositories.mentor_response_events.snapshot.assert_called_once_with(
            'account', 'session'
        )
        assert result.response == self.snapshot
        assert result.pending_learner_message_id == 'message-new'
        assert (
            self.repositories.mentor_messages.find_pending_learner_message_id.call_args_list
            == [call('account', 'session'), call('account', 'session')]
        )
        assert result.messages.items == [self.message]
        assert result.session.updated_at == self.now
        assert result.session.last_activity_at == self.now
        self.repositories.mentor_sessions.record_activity.assert_called_once_with(
            result.session
        )

    def test_should_reauthorize_replay_original_operation_and_return_current_history(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            mentor_submission_fingerprint('texto', None),
        )
        result = self.subject.execute(
            'account',
            'session',
            MentorSubmission(submission_key=self.key, content='texto'),
        )
        self.access.authorize.assert_called_once_with('account', 'operation')
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )
        assert result.response == self.snapshot
        self.repositories.mentor_response_attempts.add_submission.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_replay_empty_hint_as_same_submission_as_no_hint(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            mentor_submission_fingerprint('texto', None),
        )
        result = self.subject.execute(
            'account',
            'session',
            MentorSubmission(
                submission_key=self.key,
                content='texto',
                context_hint=MentorContextHint(),
            ),
        )
        assert self.subject.replayed is True
        assert result.response == self.snapshot
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_conflict_when_replay_changes_a_stored_v2_context_hint(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            mentor_submission_fingerprint_v2('texto', None, ()),
        )

        with pytest.raises(MentorSubmissionConflictError):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(
                    submission_key=self.key,
                    content='texto',
                    context_hint=MentorContextHint(goal_id='goal'),
                ),
            )

    @pytest.mark.parametrize('content', ['texto', '', ' \n\t '])
    @pytest.mark.parametrize(
        'status', [MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL]
    )
    def test_should_consume_batch_and_bind_selected_attachments_to_message(
        self,
        content: str,
        status: MentorAttachmentStatus,
    ) -> None:
        batch = MentorAttachmentBatch.create(
            'batch', 'account', 'session', self.now, self.now + timedelta(hours=1)
        )
        attachment = MentorAttachment.create(
            attachment_id='attachment',
            account_id='account',
            batch_id='batch',
            upload_key='upload',
            filename='worksheet.pdf',
            media_type='application/pdf',
            size_bytes=1,
            checksum='a' * 64,
            object_key='private/worksheet.pdf',
            now=self.now,
        )
        attachment.status = status
        self.repositories.mentor_attachment_batches.find_by_id.return_value = batch
        self.repositories.mentor_attachments.find_by_id.return_value = attachment

        self.subject.execute(
            'account',
            'session',
            MentorSubmission(
                submission_key=self.key,
                content=content,
                attachment_batch_id='batch',
                attachment_ids=('attachment',),
            ),
        )

        message = self.repositories.mentor_messages.add.call_args.args[0]
        assert message.content == content
        assert batch.consumed_by_message_id == message.id
        assert (attachment.session_id, attachment.message_id) == ('session', message.id)
        self.repositories.mentor_attachments.update.assert_called_once_with(attachment)
        self.repositories.mentor_attachment_batches.update.assert_called_once_with(
            batch
        )
        assert self.repositories.mentor_attachment_batches.find_by_id.call_args_list[
            -1
        ].args == ('batch',)

    @pytest.mark.parametrize('content', ['texto', '', ' \n\t '])
    @pytest.mark.parametrize(
        'status', [MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL]
    )
    def test_should_replay_exact_attachment_selection_without_rebinding(
        self, content: str, status: MentorAttachmentStatus
    ) -> None:
        batch = MentorAttachmentBatch.create(
            'batch', 'account', 'session', self.now, self.now + timedelta(hours=1)
        )
        batch.consume(self.attempt.learner_message_id)
        attachment = MentorAttachment.create(
            attachment_id='attachment',
            account_id='account',
            batch_id='batch',
            upload_key='upload',
            filename='worksheet.pdf',
            media_type='application/pdf',
            size_bytes=1,
            checksum='a' * 64,
            object_key='private/worksheet.pdf',
            now=self.now,
        )
        attachment.status = status
        attachment.bind('session', self.attempt.learner_message_id)
        self.repositories.mentor_attachments.find_by_id.return_value = attachment
        self.repositories.mentor_attachments.find_by_message_id.return_value = (
            attachment,
        )
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            mentor_submission_fingerprint_v2(
                content, None, ((attachment.id, attachment.checksum),)
            ),
        )

        self.subject.execute(
            'account',
            'session',
            MentorSubmission(
                submission_key=self.key,
                content=content,
                attachment_batch_id='batch',
                attachment_ids=('attachment',),
            ),
        )

        assert self.subject.replayed is True
        self.repositories.mentor_attachments.find_by_message_id.assert_called_once_with(
            self.attempt.learner_message_id
        )
        self.repositories.mentor_attachments.update.assert_not_called()
        self.repositories.mentor_attachment_batches.find_by_id.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

        with pytest.raises(MentorSubmissionConflictError):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(
                    submission_key=self.key,
                    content=content + 'changed',
                    attachment_batch_id='batch',
                    attachment_ids=('attachment',),
                ),
            )
        self.repositories.mentor_messages.add.assert_not_called()

    @pytest.mark.parametrize(
        'status',
        [
            MentorAttachmentStatus.UPLOADING,
            MentorAttachmentStatus.PROCESSING,
            MentorAttachmentStatus.FAILED,
            MentorAttachmentStatus.REMOVED,
        ],
    )
    def test_should_reject_unready_attachment_only_continuation_without_writes(
        self, status: MentorAttachmentStatus
    ) -> None:
        batch = MentorAttachmentBatch.create(
            'batch',
            'account',
            'session',
            self.now,
            self.now + timedelta(hours=1),
        )
        attachment = MentorAttachment.create(
            attachment_id='attachment',
            account_id='account',
            batch_id='batch',
            upload_key='upload',
            filename='image.png',
            media_type='image/png',
            size_bytes=20,
            checksum='a' * 64,
            object_key='private/image.png',
            now=self.now,
        )
        attachment.status = status
        self.repositories.mentor_attachment_batches.find_by_id.return_value = batch
        self.repositories.mentor_attachments.find_by_id.return_value = attachment

        with pytest.raises(MentorAttachmentConflictError):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(
                    submission_key=self.key,
                    content='',
                    attachment_batch_id='batch',
                    attachment_ids=('attachment',),
                ),
            )

        assert batch.consumed_by_message_id is None
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_attachments.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_fail_closed_when_identifier_port_cannot_identify_learner_message(
        self,
    ) -> None:
        self.identifiers.generate.side_effect = ['', 'attempt-new']
        with pytest.raises(ValueError, match='Incomplete response attempt'):
            self.subject.execute(
                'account',
                'session',
                MentorSubmission(submission_key=self.key, content='texto'),
            )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.add.assert_not_called()
        self.repositories.mentor_response_attempts.add_submission.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.events.add.assert_not_called()

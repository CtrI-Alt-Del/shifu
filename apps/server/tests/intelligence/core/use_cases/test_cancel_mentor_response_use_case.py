from dataclasses import replace
import pytest
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
)
from shifu.intelligence.core.domain.errors import (
    MentorResponseConflictError,
    MentorSubmissionConflictError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.use_cases import CancelMentorResponseUseCase
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)


class TestCancelMentorResponseUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare()
        self.subject = CancelMentorResponseUseCase(
            self.database, self.clock, self.access
        )

    def test_should_discard_partial_preserve_learner_and_fence(self) -> None:
        self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_response_events.discard_partial.assert_called_once_with(
            'attempt'
        )
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.CANCELLED,
            'revision',
        )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_remove_the_pending_proposal_of_the_cancelled_attempt(self) -> None:
        self.subject.execute('account', 'session', 'attempt', self.key)

        self.repositories.mentor_action_proposals.remove_pending_by_attempt_id.assert_called_once_with(
            'account', 'attempt'
        )

    def test_should_replay_same_cancellation_without_effects(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            'cancel:attempt',
        )
        self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_response_attempts.transition.assert_not_called()
        self.repositories.mentor_response_events.discard_partial.assert_not_called()
        self.repositories.mentor_action_proposals.remove_pending_by_attempt_id.assert_not_called()

    @pytest.mark.parametrize(
        'status',
        [
            MentorResponseStatus.COMPLETED,
            MentorResponseStatus.FAILED,
            MentorResponseStatus.CANCELLED,
        ],
    )
    def test_should_reject_terminal_response(
        self, status: MentorResponseStatus
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=status
        )
        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_response_events.discard_partial.assert_not_called()
        self.repositories.mentor_action_proposals.remove_pending_by_attempt_id.assert_not_called()

    def test_should_reject_lost_compare_and_set(self) -> None:
        self.repositories.mentor_response_attempts.transition.return_value = False
        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_response_events.discard_partial.assert_not_called()
        self.repositories.mentor_action_proposals.remove_pending_by_attempt_id.assert_not_called()

    def test_should_reject_foreign_attempt(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, account_id='other'
        )
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.access.assert_current.assert_not_called()

    def test_should_reject_key_reused_for_other_action(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            'retry:attempt',
        )
        with pytest.raises(MentorSubmissionConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)

    def test_should_return_owned_snapshot_and_publish_control_identity(self) -> None:
        result = self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.assert_called_once_with(
            'attempt'
        )
        self.repositories.mentor_response_attempts.find_current.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.find_submission.assert_called_once_with(
            'account', 'session', self.key
        )
        self.repositories.mentor_response_events.snapshot.assert_called_once_with(
            'account', 'session'
        )
        assert result == self.snapshot
        event = self.repositories.mentor_response_events.append.call_args.args[0]
        grant = self.access.assert_current.call_args.args[0]
        assert (grant.account_id, grant.access_revision, grant.operation_key) == (
            'account',
            'revision',
            'operation',
        )
        self.repositories.mentor_response_attempts.add_submission.assert_called_once_with(
            'account', 'session', self.key, 'attempt', 'cancel:attempt'
        )
        assert (
            event.session_id,
            event.attempt_id,
            event.sequence,
            event.kind,
            event.status,
            event.created_at,
        ) == (
            'session',
            'attempt',
            2,
            MentorResponseEventKind.CANCELLED,
            MentorResponseStatus.CANCELLED,
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

    def test_should_reject_superseded_attempt_without_control_writes(self) -> None:
        self.repositories.mentor_response_attempts.find_current.return_value = replace(
            self.attempt, id='newer-attempt'
        )
        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_response_attempts.add_submission.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_response_events.discard_partial.assert_not_called()

    @pytest.mark.parametrize('missing', ['attempt', 'current'])
    def test_should_hide_independently_missing_attempt_or_current(
        self, missing: str
    ) -> None:
        if missing == 'attempt':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
        else:
            self.repositories.mentor_response_attempts.find_current.return_value = None
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.mentor_response_attempts.add_submission.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_response_events.discard_partial.assert_not_called()

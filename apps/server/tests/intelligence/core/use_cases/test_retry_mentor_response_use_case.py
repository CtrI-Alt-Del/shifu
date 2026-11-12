from dataclasses import replace
from unittest.mock import Mock

import pytest
from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    MentorResponseStatus,
    MentorResponseEventKind,
)
from shifu.intelligence.core.domain.errors import (
    AiQuotaExhaustedError,
    MentorResponseConflictError,
    MentorSubmissionConflictError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.domain.structures import MentorContextHint
from shifu.intelligence.core.use_cases import RetryMentorResponseUseCase
from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    QUOTA_LIMIT,
    QUOTA_MONTH,
)
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)


class TestRetryMentorResponseUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare(MentorResponseStatus.FAILED)
        self.subject = RetryMentorResponseUseCase(
            self.database,
            self.identifiers,
            self.clock,
            self.access,
            self.quota_policy,
            self.quota_calendar,
        )

    def test_should_create_new_attempt_same_message_original_hint_operation(
        self,
    ) -> None:
        original = replace(
            self.attempt, context_hint=MentorContextHint(goal_id='original-goal')
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = original
        self.subject.execute('account', 'session', 'attempt', self.key)
        retry = self.repositories.mentor_response_attempts.add.call_args.args[0]
        assert self.subject.replayed is False
        assert retry.id != self.attempt.id
        assert retry.learner_message_id == original.learner_message_id
        assert retry.context_hint == original.context_hint
        assert retry.operation_key == original.operation_key
        assert retry.status is MentorResponseStatus.QUEUED
        self.access.authorize.assert_called_once_with('account', original.operation_key)
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_events.discard_partial.assert_called_once_with(
            'attempt'
        )
        assert (
            self.repositories.events.add.call_args.args[0].payload.attempt_id
            == retry.id
        )

    @pytest.mark.parametrize(
        'status',
        [
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.COMPLETED,
        ],
    )
    def test_should_reject_active_or_completed_attempt(
        self, status: MentorResponseStatus
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=status
        )
        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.repositories.events.add.assert_not_called()

    def test_should_replay_without_new_attempt_or_outbox(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            'retry:attempt',
        )
        self.subject.execute('account', 'session', 'attempt', self.key)
        assert self.subject.replayed is True
        self.repositories.mentor_response_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_conflict_on_reused_action_key(self) -> None:
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            'cancel:attempt',
        )
        with pytest.raises(MentorSubmissionConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)

    def test_should_hide_foreign_attempt(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, session_id='other'
        )
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.access.authorize.assert_not_called()

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
        retry = self.repositories.mentor_response_attempts.add.call_args.args[0]
        assert (
            retry.account_id,
            retry.session_id,
            retry.access_revision,
            retry.created_at,
            retry.updated_at,
        ) == ('account', 'session', 'revision', self.now, self.now)
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )
        self.repositories.mentor_response_attempts.add_submission.assert_called_once_with(
            'account', 'session', self.key, retry.id, 'retry:attempt'
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
            retry.id,
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

    def test_should_hide_foreign_account_attempt_even_with_owned_current_session(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, account_id='foreign-account'
        )
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session', 'attempt', self.key)
        self.access.authorize.assert_not_called()
        self.repositories.mentor_response_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_admit_the_retry_before_creating_its_attempt_or_event(self) -> None:
        effects = Mock()
        effects.attach_mock(self.quota_months.ensure_and_lock, 'lock_month')
        effects.attach_mock(self.quota_charges.add, 'add_charge')
        effects.attach_mock(
            self.repositories.mentor_response_events.discard_partial, 'discard'
        )
        effects.attach_mock(
            self.repositories.mentor_response_attempts.add, 'add_attempt'
        )
        effects.attach_mock(self.repositories.events.add, 'add_event')

        self.subject.execute('account', 'session', 'attempt', self.key)

        names = [entry[0] for entry in effects.mock_calls]
        assert names[:2] == ['lock_month', 'add_charge']
        assert set(names[2:]) == {'discard', 'add_attempt', 'add_event'}
        self.quota_months.ensure_and_lock.assert_called_once_with(
            'account', QUOTA_MONTH, QUOTA_LIMIT, self.now
        )
        charge = self.quota_charges.add.call_args.args[0]
        retry = self.repositories.mentor_response_attempts.add.call_args.args[0]
        assert charge.request_kind is AiQuotaRequestKind.MENTOR_RESPONSE
        assert charge.request_id == retry.id
        assert charge.request_id != 'attempt'
        assert charge.account_id == 'account'
        assert charge.charged_units == 0

    @pytest.mark.parametrize(
        'used_units', [QUOTA_LIMIT, QUOTA_LIMIT + 1, 5 * QUOTA_LIMIT]
    )
    def test_should_refuse_a_retry_at_or_above_the_limit_without_any_write(
        self, used_units: int
    ) -> None:
        self.quota_month.used_units = used_units

        with pytest.raises(AiQuotaExhaustedError):
            self.subject.execute('account', 'session', 'attempt', self.key)

        self.quota_charges.add.assert_not_called()
        self.repositories.mentor_response_events.discard_partial.assert_not_called()
        self.repositories.mentor_response_attempts.add.assert_not_called()
        self.repositories.mentor_response_attempts.add_submission.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_keep_the_charge_of_a_cancelled_attempt_when_it_is_retried(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=MentorResponseStatus.CANCELLED
        )

        self.subject.execute('account', 'session', 'attempt', self.key)

        self.quota_charges.find_for_update.assert_not_called()
        self.quota_months.update.assert_not_called()
        self.quota_charges.add.assert_called_once()

    def test_should_not_admit_a_replay(self) -> None:
        self.quota_month.used_units = QUOTA_LIMIT
        self.repositories.mentor_response_attempts.find_submission.return_value = (
            self.attempt,
            'retry:attempt',
        )

        self.subject.execute('account', 'session', 'attempt', self.key)

        assert self.subject.replayed is True
        self.quota_months.ensure_and_lock.assert_not_called()
        self.quota_charges.add.assert_not_called()

    def test_should_not_open_the_month_for_a_conflicting_retry(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=MentorResponseStatus.COMPLETED
        )

        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'attempt', self.key)

        self.quota_months.ensure_and_lock.assert_not_called()

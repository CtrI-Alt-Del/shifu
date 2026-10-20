from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.core.domain.errors import ServiceUnavailableError
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.entities import (
    MentorResponseAttempt,
    MentorSessionSummary,
)
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorSummaryExcerptKind,
    MentorSummaryFailureCode,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryDraft,
    MentorMessagesPage,
    MentorSessionSummaryState,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
    MentorSummaryMarker,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import GetMentorSessionUseCase


class TestGetMentorSessionUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = datetime(2026, 1, 1, tzinfo=UTC)
        self.session = MentorSession(
            id='session',
            account_id='account',
            title='title',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.repositories.mentor_sessions.find_by_id.return_value = self.session
        self.repositories.mentor_messages.find_many.return_value = MentorMessagesPage(
            items=[], next_cursor=None
        )
        self.repositories.mentor_messages.find_pending_learner_message_id.return_value = None
        self.repositories.mentor_session_summaries.find_ready.return_value = None
        self.repositories.mentor_session_summaries.find_failed.return_value = None
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.subject = GetMentorSessionUseCase(self.database, self.access)

    def test_should_return_owned_session_and_pending_message_state(self) -> None:
        result = self.subject.execute('account', 'session', 'older-cursor')

        assert result.session == self.session
        self.access.authorize.assert_called_once_with('account', 'read:session')
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )
        self.repositories.mentor_sessions.find_by_id.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_events.snapshot.assert_called_once_with(
            'account', 'session'
        )
        assert result.pending_learner_message_id is None
        self.repositories.mentor_messages.find_many.assert_called_once_with(
            'account', 'session', 'older-cursor'
        )

    def test_should_return_private_not_found_for_unowned_session(self) -> None:
        self.repositories.mentor_sessions.find_by_id.return_value = None

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('foreign-account', 'session')

        self.repositories.mentor_messages.find_many.assert_not_called()

    def test_should_reject_revoked_history_access_before_reading_messages(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session')
        self.repositories.mentor_messages.find_many.assert_not_called()
        self.repositories.mentor_response_events.snapshot.assert_not_called()

    def test_should_not_read_history_when_current_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session')
        self.database.transaction.assert_not_called()

    def summary(self, version: int, *, ready: bool) -> MentorSessionSummary:
        started = MentorSessionSummary.start(
            id=f'summary-{version}',
            account_id='account',
            session_id='session',
            attempt_id=f'attempt-{version}',
            version=version,
            boundary=MentorSummaryBoundary(message_id='boundary', created_at=self.now),
            covered_message_count=21,
            first_message_id='first',
            now=self.now,
        )
        if not ready:
            return started.fail(MentorSummaryFailureCode.NLP_UNAVAILABLE, self.now)
        return started.complete(
            MentorConversationSummaryDraft(
                topics=('range',),
                excerpts=(
                    MentorSummaryExcerptSpan(
                        message_id='boundary',
                        start=0,
                        end=4,
                        kind=MentorSummaryExcerptKind.DOUBT,
                    ),
                ),
                algorithm_version='v1',
            ),
            self.now,
        )

    def failed_attempt(self, version: int) -> MentorResponseAttempt:
        return MentorResponseAttempt.create(
            id=f'attempt-{version}',
            account_id='account',
            session_id='session',
            learner_message_id=f'learner-{version}',
            status=MentorResponseStatus.COMPLETED,
            context_hint=None,
            access_revision='revision',
            operation_key='operation',
            created_at=self.now,
            updated_at=self.now,
        )

    def test_should_return_an_empty_summary_state_without_summaries(self) -> None:
        assert self.subject.execute('account', 'session').summary == (
            MentorSessionSummaryState()
        )

    def test_should_expose_the_ready_marker_without_offsets(self) -> None:
        self.repositories.mentor_session_summaries.find_ready.return_value = (
            self.summary(2, ready=True)
        )
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.failed_attempt(2)
        )

        state = self.subject.execute('account', 'session').summary

        assert state == MentorSessionSummaryState(
            current=MentorSummaryMarker(
                version=2,
                boundary_message_id='boundary',
                covered_message_count=21,
                completed_at=self.now,
                after_message_id='learner-2',
            ),
            failure_after_message_id=None,
        )

    def test_should_leave_the_trigger_unknown_when_the_attempt_is_gone(self) -> None:
        self.repositories.mentor_session_summaries.find_ready.return_value = (
            self.summary(2, ready=True)
        )
        self.repositories.mentor_response_attempts.find_by_id.return_value = None

        state = self.subject.execute('account', 'session').summary

        assert state.current is not None
        assert state.current.after_message_id is None

    def test_should_leave_the_trigger_unknown_when_the_summary_lost_its_attempt(
        self,
    ) -> None:
        ready = self.summary(2, ready=True)
        self.repositories.mentor_session_summaries.find_ready.return_value = replace(
            ready, attempt_id=None
        )

        state = self.subject.execute('account', 'session').summary

        assert state.current is not None
        assert state.current.after_message_id is None
        self.repositories.mentor_response_attempts.find_by_id.assert_not_called()

    def test_should_not_expose_a_trigger_that_belongs_to_another_session(
        self,
    ) -> None:
        self.repositories.mentor_session_summaries.find_ready.return_value = (
            self.summary(2, ready=True)
        )
        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.failed_attempt(2), session_id='other-session'
        )

        state = self.subject.execute('account', 'session').summary

        assert state.current is not None
        assert state.current.after_message_id is None

    def test_should_anchor_the_failure_notice_when_only_a_failed_row_exists(
        self,
    ) -> None:
        summaries = self.repositories.mentor_session_summaries
        summaries.find_failed.return_value = self.summary(3, ready=False)
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.failed_attempt(3)
        )

        state = self.subject.execute('account', 'session').summary

        assert state.current is None
        assert state.failure_after_message_id == 'learner-3'
        self.repositories.mentor_response_attempts.find_by_id.assert_called_once_with(
            'attempt-3'
        )

    def test_should_keep_both_when_the_failed_row_is_newer_than_the_ready_one(
        self,
    ) -> None:
        summaries = self.repositories.mentor_session_summaries
        summaries.find_ready.return_value = self.summary(2, ready=True)
        summaries.find_failed.return_value = self.summary(3, ready=False)
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.failed_attempt(3)
        )

        state = self.subject.execute('account', 'session').summary

        assert state.current is not None
        assert state.current.version == 2
        assert state.failure_after_message_id == 'learner-3'

    def test_should_ignore_a_failed_row_older_than_the_ready_one(self) -> None:
        summaries = self.repositories.mentor_session_summaries
        summaries.find_ready.return_value = self.summary(4, ready=True)
        summaries.find_failed.return_value = self.summary(3, ready=False)

        state = self.subject.execute('account', 'session').summary

        assert state.failure_after_message_id is None
        # Only the ready row's trigger is looked up; the older failed row is never read.
        self.repositories.mentor_response_attempts.find_by_id.assert_called_once_with(
            'attempt-4'
        )

    def test_should_omit_the_notice_when_the_failed_attempt_is_gone(self) -> None:
        summaries = self.repositories.mentor_session_summaries
        summaries.find_failed.return_value = self.summary(3, ready=False)
        self.repositories.mentor_response_attempts.find_by_id.return_value = None

        assert (
            self.subject.execute('account', 'session').summary.failure_after_message_id
            is None
        )

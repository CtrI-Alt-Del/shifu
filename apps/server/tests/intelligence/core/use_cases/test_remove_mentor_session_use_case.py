from datetime import UTC, datetime
from unittest.mock import Mock, call, create_autospec

import pytest
from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import MentorSubmissionRecord
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import RemoveMentorSessionUseCase
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class TestRemoveMentorSessionUseCase:
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
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.repositories.mentor_sessions.find_submission_by_session_id.return_value = (
            MentorSubmissionRecord(
                session_id='session',
                content_fingerprint='fingerprint',
                deleted_at=None,
            )
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.access_provider = create_autospec(MentorAccessProvider, instance=True)
        self.subject = RemoveMentorSessionUseCase(
            self.database, self.clock, self.access_provider
        )

    def test_should_purge_messages_then_tombstone_session_in_one_transaction(
        self,
    ) -> None:
        self.subject.execute('account', 'session')

        self.repositories.mentor_messages.remove_by_session_id.assert_called_once_with(
            'session'
        )
        self.repositories.mentor_sessions.remove.assert_called_once_with(
            self.session, self.now
        )
        self.repositories.mentor_sessions.lock_session.assert_called_once_with(
            'account', 'session'
        )
        self.database.transaction.assert_called_once()

    def test_should_remove_summaries_in_the_deletion_transaction(self) -> None:
        self.subject.execute('account', 'session')

        summaries = self.repositories.mentor_session_summaries
        summaries.remove_by_session_id.assert_called_once_with('session')
        self.database.transaction.assert_called_once()

    def test_should_remove_memory_change_records_right_after_locking_the_session(
        self,
    ) -> None:
        effects = Mock()
        effects.attach_mock(self.repositories.mentor_sessions.lock_session, 'lock')
        effects.attach_mock(
            self.repositories.learner_memory_changes.remove_by_session_id, 'changes'
        )

        self.subject.execute('account', 'session')

        assert effects.mock_calls[:2] == [
            call.lock('account', 'session'),
            call.changes('session'),
        ]
        self.repositories.learner_memories.remove.assert_not_called()
        self.repositories.learner_memories.remove_by_account_id.assert_not_called()
        self.database.transaction.assert_called_once()

    def test_should_not_touch_memory_data_for_an_unknown_or_foreign_session(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_submission_by_session_id.return_value = (
            None
        )

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('foreign-account', 'session')

        self.repositories.learner_memory_changes.remove_by_session_id.assert_not_called()

    def test_should_not_touch_summaries_for_an_unknown_or_already_deleted_session(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_submission_by_session_id.return_value = (
            None
        )
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('foreign-account', 'session')
        self.repositories.mentor_session_summaries.remove_by_session_id.assert_not_called()

    def test_should_make_owned_tombstone_repeat_successful(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        self.repositories.mentor_sessions.find_submission_by_session_id.return_value = (
            MentorSubmissionRecord(
                session_id='session', content_fingerprint=None, deleted_at=self.now
            )
        )

        self.subject.execute('account', 'session')

        self.repositories.mentor_messages.remove_by_session_id.assert_not_called()
        self.repositories.mentor_sessions.remove.assert_not_called()
        self.repositories.mentor_sessions.find_submission_by_session_id.assert_called_with(
            'account', 'session'
        )
        assert (
            self.repositories.mentor_sessions.find_submission_by_session_id.call_count
            == 2
        )
        self.repositories.mentor_sessions.lock_session.assert_called_once_with(
            'account', 'session'
        )

    def test_should_not_treat_an_active_submission_with_missing_session_as_deleted(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        self.repositories.mentor_sessions.find_submission_by_session_id.return_value = (
            MentorSubmissionRecord(
                session_id='session',
                content_fingerprint='fingerprint',
                deleted_at=None,
            )
        )

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session')

        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_sessions.find_submission_by_session_id.assert_called_with(
            'account', 'session'
        )
        assert (
            self.repositories.mentor_sessions.find_submission_by_session_id.call_count
            == 2
        )
        self.repositories.mentor_messages.remove_by_session_id.assert_not_called()
        self.repositories.mentor_sessions.remove.assert_not_called()

    def test_should_hide_unknown_or_foreign_session(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        self.repositories.mentor_sessions.find_submission_by_session_id.return_value = (
            None
        )

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('foreign-account', 'session')

        self.repositories.mentor_sessions.find_submission_by_session_id.assert_called_once_with(
            'foreign-account', 'session'
        )
        self.repositories.mentor_sessions.find_by_id_for_update.assert_not_called()
        self.repositories.mentor_sessions.lock_session.assert_not_called()
        self.repositories.mentor_messages.remove_by_session_id.assert_not_called()
        self.repositories.mentor_sessions.remove.assert_not_called()

    def test_should_purge_stream_attempts_messages_before_tombstone(self) -> None:
        effects = Mock()
        effects.attach_mock(self.repositories.mentor_sessions.lock_session, 'lock')
        effects.attach_mock(
            self.repositories.learner_memory_changes.remove_by_session_id, 'memories'
        )
        effects.attach_mock(
            self.repositories.mentor_session_summaries.remove_by_session_id, 'summaries'
        )
        effects.attach_mock(
            self.repositories.mentor_response_events.remove_by_session_id, 'events'
        )
        effects.attach_mock(
            self.repositories.mentor_response_attempts.remove_by_session_id, 'attempts'
        )
        effects.attach_mock(
            self.repositories.mentor_messages.remove_by_session_id, 'messages'
        )
        effects.attach_mock(self.repositories.mentor_sessions.remove, 'session')
        self.subject.execute('account', 'session')
        assert effects.mock_calls == [
            call.lock('account', 'session'),
            call.memories('session'),
            call.summaries('session'),
            call.events('session'),
            call.attempts('session'),
            call.messages('session'),
            call.session(self.session, self.now),
        ]

    def test_should_reject_submission_removed_while_waiting_for_lock(self) -> None:
        active = (
            self.repositories.mentor_sessions.find_submission_by_session_id.return_value
        )
        self.repositories.mentor_sessions.find_submission_by_session_id.side_effect = [
            active,
            None,
        ]
        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session')
        self.repositories.mentor_response_events.remove_by_session_id.assert_not_called()
        self.repositories.mentor_response_attempts.remove_by_session_id.assert_not_called()
        self.repositories.mentor_messages.remove_by_session_id.assert_not_called()
        self.repositories.mentor_sessions.remove.assert_not_called()

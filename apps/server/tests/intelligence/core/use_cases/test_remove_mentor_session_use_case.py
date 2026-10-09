from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import MentorSubmissionRecord
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import RemoveMentorSessionUseCase
from shifu.shared.core.interfaces import ClockProvider


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
        self.subject = RemoveMentorSessionUseCase(self.database, self.clock)

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

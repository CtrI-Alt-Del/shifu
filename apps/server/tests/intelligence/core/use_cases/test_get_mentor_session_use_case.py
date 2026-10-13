from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.core.domain.errors import ServiceUnavailableError
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import MentorMessagesPage
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

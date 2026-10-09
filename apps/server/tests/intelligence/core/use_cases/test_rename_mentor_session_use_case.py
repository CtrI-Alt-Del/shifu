from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import RenameMentorSessionUseCase
from shifu.shared.core.interfaces import ClockProvider


class TestRenameMentorSessionUseCase:
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
            title='old',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.subject = RenameMentorSessionUseCase(self.database, self.clock)

    def test_should_trim_and_rename_without_changing_activity_order(self) -> None:
        activity = self.session.last_activity_at

        result = self.subject.execute('account', 'session', '  Novo título  ')

        assert result.title == 'Novo título'
        assert result.updated_at == self.now
        assert result.last_activity_at == activity
        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_sessions.rename.assert_called_once_with(self.session)

    @pytest.mark.parametrize('title', ['', '  ', 'x' * 121])
    def test_should_reject_invalid_title_without_repository_access(
        self, title: str
    ) -> None:
        with pytest.raises(MentorInputInvalidError):
            self.subject.execute('account', 'session', title)

        self.database.transaction.assert_not_called()

    def test_should_hide_foreign_session(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('foreign-account', 'session', 'New title')

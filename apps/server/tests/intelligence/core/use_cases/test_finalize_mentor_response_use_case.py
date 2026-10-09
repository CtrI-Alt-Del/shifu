from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.domain.errors import MentorResponseConflictError
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import FinalizeMentorResponseUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestFinalizeMentorResponseUseCase:
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
        self.learner_message = MentorMessage(
            id='learner-message',
            session_id='session',
            role=MentorMessageRole.LEARNER,
            content='question',
            created_at=self.now,
            in_reply_to_message_id=None,
        )
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.repositories.mentor_messages.find_by_id.return_value = self.learner_message
        self.repositories.mentor_messages.find_response.return_value = None
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = 'mentor-message'
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.subject = FinalizeMentorResponseUseCase(
            self.database, self.identifiers, self.clock
        )

    def test_should_persist_one_response_and_activity_under_session_lock(self) -> None:
        assert (
            self.subject.execute('account', 'session', 'learner-message', 'answer')
            is True
        )

        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        persisted = self.repositories.mentor_messages.add.call_args.args[0]
        assert persisted.id == 'mentor-message'
        assert persisted.session_id == 'session'
        assert persisted.role is MentorMessageRole.MENTOR
        assert persisted.in_reply_to_message_id == 'learner-message'
        assert persisted.content == 'answer'
        assert persisted.created_at == self.now
        assert self.session.updated_at == self.now
        assert self.session.last_activity_at == self.now
        self.repositories.mentor_sessions.record_activity.assert_called_once_with(
            self.session
        )
        self.repositories.mentor_messages.find_by_id.assert_called_once_with(
            'account', 'session', 'learner-message'
        )
        self.repositories.mentor_messages.find_response.assert_called_once_with(
            'account', 'session', 'learner-message'
        )

    def test_should_treat_exact_response_replay_as_success(self) -> None:
        self.repositories.mentor_messages.find_response.return_value = MentorMessage(
            id='response',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='answer',
            created_at=self.now,
            in_reply_to_message_id='learner-message',
        )

        assert (
            self.subject.execute('account', 'session', 'learner-message', 'answer')
            is True
        )

        self.repositories.mentor_messages.add.assert_not_called()
        self.identifiers.generate.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()
        assert self.session.updated_at == self.now
        assert self.session.last_activity_at == self.now

    def test_should_conflict_on_divergent_response_replay(self) -> None:
        self.repositories.mentor_messages.find_response.return_value = MentorMessage(
            id='response',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='other',
            created_at=self.now,
            in_reply_to_message_id='learner-message',
        )

        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'learner-message', 'answer')

        self.repositories.mentor_messages.add.assert_not_called()
        self.identifiers.generate.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()

    def test_should_return_false_when_learner_message_is_not_visible_to_account(
        self,
    ) -> None:
        self.repositories.mentor_messages.find_by_id.return_value = None

        assert (
            self.subject.execute('account', 'session', 'foreign-message', 'answer')
            is False
        )

        self.repositories.mentor_messages.find_by_id.assert_called_once_with(
            'account', 'session', 'foreign-message'
        )
        self.repositories.mentor_messages.find_response.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()

    def test_should_return_false_for_deleted_or_missing_targets(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None

        assert (
            self.subject.execute('account', 'deleted', 'learner-message', 'answer')
            is False
        )

        self.repositories.mentor_messages.find_by_id.assert_not_called()

    def test_should_reject_non_learner_reply_target(self) -> None:
        self.repositories.mentor_messages.find_by_id.return_value = MentorMessage(
            id='mentor',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='old answer',
            created_at=self.now,
            in_reply_to_message_id='another',
        )

        with pytest.raises(MentorResponseConflictError):
            self.subject.execute('account', 'session', 'mentor', 'answer')

        self.repositories.mentor_messages.add.assert_not_called()

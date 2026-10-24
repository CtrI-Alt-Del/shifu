from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorMessage,
    MentorSession,
    MentorSessionSummary,
)
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorSummaryExcerptKind,
)
from shifu.intelligence.core.domain.errors import MentorSessionSummaryNotFoundError
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
    MentorSessionSummaryContent,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorMessagesRepository,
    MentorSessionsRepository,
    MentorSessionSummariesRepository,
)
from shifu.intelligence.core.use_cases import GetMentorSessionSummaryUseCase
from shifu.shared.core.domain.errors import AuthorizationError, ServiceUnavailableError
from shifu.shared.core.interfaces import MentorAccessProvider


class TestGetMentorSessionSummaryUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.now = datetime(2026, 10, 10, tzinfo=UTC)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.sessions = create_autospec(MentorSessionsRepository, instance=True)
        self.summaries = create_autospec(
            MentorSessionSummariesRepository, instance=True
        )
        self.messages = create_autospec(MentorMessagesRepository, instance=True)
        self.repositories.mentor_sessions = self.sessions
        self.repositories.mentor_session_summaries = self.summaries
        self.repositories.mentor_messages = self.messages
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.sessions.find_by_id.return_value = MentorSession(
            id='session',
            account_id='account',
            title='title',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.learner = MentorMessage(
            id='m01',
            session_id='session',
            role=MentorMessageRole.LEARNER,
            content='Meu laço não mostra o último item.',
            created_at=self.now,
            in_reply_to_message_id=None,
        )
        self.mentor = MentorMessage(
            id='m02',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='Veja os índices que range produz.',
            created_at=self.now + timedelta(minutes=1),
            in_reply_to_message_id='m01',
        )
        started = MentorSessionSummary.start(
            id='summary',
            account_id='account',
            session_id='session',
            attempt_id='attempt',
            version=2,
            boundary=MentorSummaryBoundary(
                message_id='m02', created_at=self.mentor.created_at
            ),
            covered_message_count=21,
            first_message_id='m01',
            now=self.now,
        )
        self.summary = started.complete(
            MentorConversationSummaryDraft(
                topics=('range', 'laço'),
                excerpts=(
                    MentorSummaryExcerptSpan(
                        message_id='m02',
                        start=0,
                        end=33,
                        kind=MentorSummaryExcerptKind.GUIDANCE,
                    ),
                    MentorSummaryExcerptSpan(
                        message_id='m01',
                        start=0,
                        end=34,
                        kind=MentorSummaryExcerptKind.DOUBT,
                    ),
                ),
                algorithm_version='textrank-v1',
            ),
            self.now,
        )
        self.summaries.find_ready.return_value = self.summary
        self.messages.find_by_ids.return_value = (self.learner, self.mentor)
        self.subject = GetMentorSessionSummaryUseCase(self.database, self.access)

    def test_should_render_the_ready_summary_for_the_owner(self) -> None:
        result = self.subject.execute('account', 'session')

        rendered = MentorConversationSummaryContext.from_summary(
            self.summary, (self.learner, self.mentor)
        )
        assert result == MentorSessionSummaryContent(
            version=2,
            text=rendered.text,
            covered_message_count=21,
            first_message_id='m01',
        )
        assert rendered.text.startswith(
            'Nesta conversa, os assuntos foram range e laço.'
        )
        self.access.authorize.assert_called_once_with('account', 'read:session')
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )
        self.summaries.find_ready.assert_called_once_with('account', 'session')
        self.messages.find_by_ids.assert_called_once_with(
            'account', 'session', ('m02', 'm01')
        )

    @pytest.mark.parametrize('case', ['absent_or_foreign_or_tombstoned', 'no_summary'])
    def test_should_answer_not_found_identically(self, case: str) -> None:
        if case == 'no_summary':
            self.summaries.find_ready.return_value = None
        else:
            self.sessions.find_by_id.return_value = None

        with pytest.raises(MentorSessionSummaryNotFoundError) as error:
            self.subject.execute('other-account', 'session')

        assert error.value.message == 'Resumo da conversa não encontrado.'
        self.messages.find_by_ids.assert_not_called()

    def test_should_not_read_anything_when_access_is_revoked(self) -> None:
        self.access.assert_current.side_effect = AuthorizationError()

        with pytest.raises(AuthorizationError):
            self.subject.execute('account', 'session')

        self.database.transaction.assert_not_called()

    def test_should_not_read_anything_when_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session')

        self.database.transaction.assert_not_called()

    def test_should_fail_closed_when_a_source_message_is_missing(self) -> None:
        self.messages.find_by_ids.return_value = (replace(self.learner),)

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session')

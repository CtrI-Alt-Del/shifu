from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.intelligence.entities import MentorActionProposalFaker
from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.enums import (
    MentorActionProposalOutcome,
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.errors import (
    MentorActionProposalFinalizedError,
    MentorSessionNotFoundError,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorActionProposalsRepository,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import DeclineMentorActionProposalUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class TestDeclineMentorActionProposalUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.now = datetime(2026, 10, 10, tzinfo=UTC)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.sessions = create_autospec(MentorSessionsRepository, instance=True)
        self.proposals = create_autospec(MentorActionProposalsRepository, instance=True)
        self.repositories.mentor_sessions = self.sessions
        self.repositories.mentor_action_proposals = self.proposals
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.session = MentorSession(
            id='session',
            account_id='account',
            title='Conversa',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.proposal = MentorActionProposalFaker.fake(
            id='proposal',
            account_id='account',
            session_id='session',
            learner_message_id='message',
        )
        self.sessions.find_by_id_for_update.return_value = self.session
        self.proposals.find_by_id_for_update.return_value = self.proposal
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.subject = DeclineMentorActionProposalUseCase(
            self.database, self.clock, self.access
        )

    def test_should_persist_declined_and_return_the_current_item(self) -> None:
        item = self.subject.execute('account', 'session', 'proposal')

        assert self.proposal.status is MentorActionProposalStatus.DECLINED
        assert self.proposal.updated_at == self.now
        self.proposals.update.assert_called_once_with(self.proposal)
        assert item.id == 'proposal'
        assert item.source_message_id == 'message'
        assert item.status is MentorActionProposalStatus.DECLINED
        assert item.outcome is None

    def test_should_revalidate_access_before_reading_the_proposal(self) -> None:
        self.subject.execute('account', 'session', 'proposal')

        self.access.authorize.assert_called_once_with(
            'account', 'action-proposal:decline:proposal'
        )
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )

    def test_should_lock_the_session_before_the_proposal(self) -> None:
        self.subject.execute('account', 'session', 'proposal')

        self.sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.proposals.find_by_id_for_update.assert_called_once_with(
            'account', 'proposal'
        )

    def test_should_stop_when_access_is_revoked(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session', 'proposal')

        self.database.transaction.assert_not_called()
        self.proposals.update.assert_not_called()

    def test_should_hide_an_unknown_or_foreign_conversation(self) -> None:
        self.sessions.find_by_id_for_update.return_value = None

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'foreign', 'proposal')

        self.proposals.find_by_id_for_update.assert_not_called()
        self.proposals.update.assert_not_called()

    def test_should_hide_an_unknown_or_foreign_proposal(self) -> None:
        self.proposals.find_by_id_for_update.return_value = None

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session', 'missing')

        self.proposals.update.assert_not_called()

    def test_should_hide_a_proposal_of_another_conversation(self) -> None:
        self.proposals.find_by_id_for_update.return_value = (
            MentorActionProposalFaker.fake(
                id='proposal', account_id='account', session_id='other-session'
            )
        )

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session', 'proposal')

        self.proposals.update.assert_not_called()

    @pytest.mark.parametrize(
        'status',
        [
            MentorActionProposalStatus.DECLINED,
            MentorActionProposalStatus.COMPLETED,
            MentorActionProposalStatus.REJECTED,
        ],
    )
    def test_should_refuse_a_proposal_that_is_not_pending(
        self, status: MentorActionProposalStatus
    ) -> None:
        self.proposal.status = status
        self.proposal.outcome = (
            MentorActionProposalOutcome.ADDED
            if status is MentorActionProposalStatus.COMPLETED
            else None
        )

        with pytest.raises(MentorActionProposalFinalizedError):
            self.subject.execute('account', 'session', 'proposal')

        self.proposals.update.assert_not_called()
        assert self.proposal.status is status

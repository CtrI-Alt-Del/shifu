from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorActionProposalsRepository,
)
from shifu.intelligence.core.use_cases import (
    PurgeMentorActionProposalsForAccountUseCase,
)


class TestPurgeMentorActionProposalsForAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.proposals = create_autospec(MentorActionProposalsRepository, instance=True)
        self.repositories.mentor_action_proposals = self.proposals
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = PurgeMentorActionProposalsForAccountUseCase(self.database)

    def test_should_remove_the_proposals_of_the_account_in_one_transaction(
        self,
    ) -> None:
        self.proposals.remove_by_account_id.return_value = 3

        assert self.subject.execute('account') == 3

        self.proposals.remove_by_account_id.assert_called_once_with('account')
        self.database.transaction.assert_called_once()

    def test_should_return_zero_when_the_account_has_no_proposals(self) -> None:
        self.proposals.remove_by_account_id.return_value = 0

        assert self.subject.execute('account') == 0

    def test_should_remove_only_proposals_and_leave_other_data_alone(self) -> None:
        self.proposals.remove_by_account_id.return_value = 1

        self.subject.execute('account')

        self.repositories.mentor_sessions.remove.assert_not_called()
        self.repositories.learner_memories.remove_by_account_id.assert_not_called()

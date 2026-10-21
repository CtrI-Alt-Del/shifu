from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorSessionSummariesRepository,
)
from shifu.intelligence.core.use_cases import PurgeMentorSummariesForAccountUseCase


class TestPurgeMentorSummariesForAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.summaries = create_autospec(
            MentorSessionSummariesRepository, instance=True
        )
        self.repositories.mentor_session_summaries = self.summaries
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = PurgeMentorSummariesForAccountUseCase(self.database)

    def test_should_remove_every_summary_of_the_account_in_one_transaction(
        self,
    ) -> None:
        self.summaries.remove_by_account_id.return_value = 3

        assert self.subject.execute('account') == 3

        self.summaries.remove_by_account_id.assert_called_once_with('account')
        self.database.transaction.assert_called_once()

    def test_should_return_zero_on_repeated_delivery(self) -> None:
        self.summaries.remove_by_account_id.side_effect = [2, 0]

        assert self.subject.execute('account') == 2
        assert self.subject.execute('account') == 0

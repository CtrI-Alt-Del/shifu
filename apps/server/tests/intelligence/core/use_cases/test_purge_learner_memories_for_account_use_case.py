from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoriesRepository,
    LearnerMemoryChangesRepository,
)
from shifu.intelligence.core.use_cases import PurgeLearnerMemoriesForAccountUseCase


class TestPurgeLearnerMemoriesForAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.memories = create_autospec(LearnerMemoriesRepository, instance=True)
        self.changes = create_autospec(LearnerMemoryChangesRepository, instance=True)
        self.repositories.learner_memories = self.memories
        self.repositories.learner_memory_changes = self.changes
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = PurgeLearnerMemoriesForAccountUseCase(self.database)

    def test_should_lock_the_account_before_removing_change_records_then_memories(
        self,
    ) -> None:
        self.changes.remove_by_account_id.return_value = 2
        self.memories.remove_by_account_id.return_value = 3
        effects = Mock()
        effects.attach_mock(self.memories.lock_account, 'lock')
        effects.attach_mock(self.changes.remove_by_account_id, 'changes')
        effects.attach_mock(self.memories.remove_by_account_id, 'memories')

        assert self.subject.execute('account') == 5

        assert effects.mock_calls == [
            call.lock('account'),
            call.changes('account'),
            call.memories('account'),
        ]
        self.database.transaction.assert_called_once()

    def test_should_return_zero_on_repeated_delivery(self) -> None:
        self.changes.remove_by_account_id.side_effect = [1, 0]
        self.memories.remove_by_account_id.side_effect = [1, 0]

        assert self.subject.execute('account') == 2
        assert self.subject.execute('account') == 0

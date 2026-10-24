from unittest.mock import create_autospec

import pytest

from shifu.fakers.intelligence.entities.learner_memory_faker import LearnerMemoryFaker
from shifu.intelligence.core.domain.errors import LearnerMemoryNotFoundError
from shifu.intelligence.core.domain.structures import LearnerMemoryDetails
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoriesRepository,
)
from shifu.intelligence.core.use_cases import GetLearnerMemoryUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import MentorAccessProvider


class TestGetLearnerMemoryUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.memories = create_autospec(LearnerMemoriesRepository, instance=True)
        self.repositories.learner_memories = self.memories
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.subject = GetLearnerMemoryUseCase(self.database, self.access)

    def test_should_return_an_owned_memory(self) -> None:
        details = LearnerMemoryDetails(
            memory=LearnerMemoryFaker.fake(id='memory', account_id='account'),
            origins=(),
            concepts=(),
        )
        self.memories.find_details.return_value = details

        assert self.subject.execute('account', 'memory') == details

        self.memories.find_details.assert_called_once_with('account', 'memory')
        self.access.authorize.assert_called_once_with('account', 'memory:read:memory')
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )

    def test_should_report_the_same_error_for_absent_and_foreign_memories(self) -> None:
        self.memories.find_details.return_value = None

        with pytest.raises(LearnerMemoryNotFoundError):
            self.subject.execute('another-account', 'memory')

        self.memories.find_details.assert_called_once_with('another-account', 'memory')

    def test_should_not_read_when_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'memory')

        self.database.transaction.assert_not_called()
        self.memories.find_details.assert_not_called()

    def test_should_not_read_when_the_access_revision_changed(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'memory')

        self.database.transaction.assert_not_called()
        self.memories.find_details.assert_not_called()

from unittest.mock import create_autospec

import pytest

from shifu.fakers.intelligence.entities.learner_memory_faker import LearnerMemoryFaker
from shifu.intelligence.core.domain.enums import LearnerMemoryCategory
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryDetails,
    LearnerMemoryFilter,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoriesRepository,
)
from shifu.intelligence.core.use_cases import ListLearnerMemoriesUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import MentorAccessProvider


class TestListLearnerMemoriesUseCase:
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
        self.subject = ListLearnerMemoriesUseCase(self.database, self.access)

    def test_should_list_only_the_requesting_accounts_memories(self) -> None:
        details = LearnerMemoryDetails(
            memory=LearnerMemoryFaker.fake(account_id='account'),
            origins=(),
            concepts=(),
        )
        self.memories.find_many.return_value = (details,)
        memory_filter = LearnerMemoryFilter(
            query='exemplos', category=LearnerMemoryCategory.EXPLANATION_PREFERENCE
        )

        result = self.subject.execute('account', memory_filter)

        assert result == (details,)
        self.memories.find_many.assert_called_once_with('account', memory_filter)
        self.access.authorize.assert_called_once_with('account', 'memory:list')
        self.access.assert_current.assert_called_once_with(
            self.access.authorize.return_value
        )

    def test_should_treat_an_empty_query_as_no_search(self) -> None:
        self.memories.find_many.return_value = ()

        assert self.subject.execute('account', LearnerMemoryFilter(query='')) == ()

        self.memories.find_many.assert_called_once_with(
            'account', LearnerMemoryFilter(query=None, category=None)
        )

    def test_should_not_read_when_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', LearnerMemoryFilter())

        self.database.transaction.assert_not_called()
        self.memories.find_many.assert_not_called()

    def test_should_not_read_when_the_access_revision_changed(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', LearnerMemoryFilter())

        self.database.transaction.assert_not_called()
        self.memories.find_many.assert_not_called()

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.fakers.intelligence.entities.learner_memory_faker import LearnerMemoryFaker
from shifu.intelligence.core.domain.errors import (
    LearnerMemoryConflictError,
    LearnerMemoryContentInvalidError,
    LearnerMemoryNotFoundError,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryConcept,
    LearnerMemoryDetails,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoriesRepository,
    LearnerMemoryAnalyzerProvider,
    LearnerMemoryChangesRepository,
)
from shifu.intelligence.core.use_cases import EditLearnerMemoryUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class TestEditLearnerMemoryUseCase:
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
        self.analyzer = create_autospec(LearnerMemoryAnalyzerProvider, instance=True)
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        self.now = self.created_at + timedelta(days=1)
        self.clock.now.return_value = self.now
        self.memory = LearnerMemoryFaker.fake(
            id='memory',
            account_id='account',
            content='Prefiro exemplos em Python.',
            version=1,
            created_at=self.created_at,
        )
        self.concepts = (LearnerMemoryConcept(key='javascript', label='JavaScript'),)
        self.details = LearnerMemoryDetails(
            memory=self.memory, origins=(), concepts=self.concepts
        )
        self.memories.find_by_id_for_update.return_value = self.memory
        self.memories.find_details.return_value = self.details
        self.analyzer.concepts.return_value = self.concepts
        self.subject = EditLearnerMemoryUseCase(
            self.database, self.analyzer, self.access, self.clock
        )

    def test_should_edit_content_recompute_concepts_and_advance_the_version(
        self,
    ) -> None:
        result = self.subject.execute(
            'account', 'memory', '  Prefiro exemplos em JavaScript.  ', 1
        )

        assert result == self.details
        assert self.memory.content == 'Prefiro exemplos em JavaScript.'
        assert self.memory.version == 2
        assert self.memory.last_declared_at == self.now
        assert self.memory.updated_at == self.now
        self.analyzer.concepts.assert_called_once_with(
            'Prefiro exemplos em JavaScript.'
        )
        self.memories.update.assert_called_once_with(self.memory, self.concepts)
        self.database.transaction.assert_called_once()
        self.access.authorize.assert_called_once_with('account', 'memory:edit:memory')

    def test_should_compute_concepts_before_taking_the_account_lock_and_load_then_write(
        self,
    ) -> None:
        effects = Mock()
        effects.attach_mock(self.analyzer.concepts, 'concepts')
        effects.attach_mock(self.memories.lock_account, 'lock')
        effects.attach_mock(self.memories.find_by_id_for_update, 'find')
        effects.attach_mock(self.memories.update, 'update')

        self.subject.execute('account', 'memory', 'Prefiro exemplos curtos.', 1)

        assert effects.mock_calls == [
            call.concepts('Prefiro exemplos curtos.'),
            call.lock('account'),
            call.find('account', 'memory'),
            call.update(self.memory, self.concepts),
        ]

    def test_should_not_create_a_change_record_or_a_marker(self) -> None:
        self.subject.execute('account', 'memory', 'Prefiro exemplos curtos.', 1)

        assert self.changes.method_calls == []

    def test_should_reject_a_stale_version_without_changing_the_memory(self) -> None:
        self.memory.version = 2

        with pytest.raises(LearnerMemoryConflictError):
            self.subject.execute('account', 'memory', 'Prefiro exemplos curtos.', 1)

        assert self.memory.content == 'Prefiro exemplos em Python.'
        assert self.memory.version == 2
        self.memories.update.assert_not_called()

    @pytest.mark.parametrize('content', ['', '   ', 'x' * 281])
    def test_should_reject_empty_and_oversized_content(self, content: str) -> None:
        with pytest.raises(LearnerMemoryContentInvalidError):
            self.subject.execute('account', 'memory', content, 1)

        assert self.memory.version == 1
        self.memories.update.assert_not_called()
        self.analyzer.concepts.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_accept_content_of_exactly_280_code_points(self) -> None:
        self.subject.execute('account', 'memory', 'x' * 280, 1)

        assert self.memory.content == 'x' * 280
        self.memories.update.assert_called_once()

    def test_should_report_the_same_error_for_absent_and_foreign_memories(
        self,
    ) -> None:
        self.memories.find_by_id_for_update.return_value = None

        with pytest.raises(LearnerMemoryNotFoundError):
            self.subject.execute('another-account', 'memory', 'Prefiro curtos.', 1)

        self.memories.find_by_id_for_update.assert_called_once_with(
            'another-account', 'memory'
        )
        self.memories.update.assert_not_called()

    def test_should_not_touch_any_repository_when_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'memory', 'Prefiro curtos.', 1)

        self.database.transaction.assert_not_called()
        self.memories.lock_account.assert_not_called()
        self.analyzer.concepts.assert_not_called()

    def test_should_not_touch_any_repository_when_the_access_revision_changed(
        self,
    ) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'memory', 'Prefiro curtos.', 1)

        self.database.transaction.assert_not_called()
        self.memories.lock_account.assert_not_called()
        self.memories.update.assert_not_called()

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call, create_autospec

import pytest

from shifu.fakers.intelligence.entities.learner_memory_faker import LearnerMemoryFaker
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoriesRepository,
    LearnerMemoryChangesRepository,
)
from shifu.intelligence.core.use_cases import RemoveLearnerMemoryUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class TestRemoveLearnerMemoryUseCase:
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
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 2, tzinfo=UTC)
        self.clock.now.return_value = self.now
        self.memories.lock_account.return_value = None
        self.memories.find_by_id_for_update.return_value = LearnerMemoryFaker.fake(
            id='memory', account_id='account'
        )
        self.subject = RemoveLearnerMemoryUseCase(
            self.database, self.access, self.clock
        )

    def test_should_erase_change_texts_before_removing_the_memory_and_advance_the_fence(
        self,
    ) -> None:
        effects = Mock()
        effects.attach_mock(self.memories.lock_account, 'lock')
        effects.attach_mock(self.memories.find_by_id_for_update, 'find')
        effects.attach_mock(self.changes.erase_by_memory_id, 'erase')
        effects.attach_mock(self.memories.remove, 'remove')
        effects.attach_mock(self.memories.advance_fence, 'fence')

        self.subject.execute('account', 'memory')

        assert effects.mock_calls == [
            call.lock('account'),
            call.find('account', 'memory'),
            call.erase('account', 'memory'),
            call.remove('account', 'memory'),
            call.fence('account', self.now),
        ]
        self.database.transaction.assert_called_once()
        self.access.authorize.assert_called_once_with('account', 'memory:remove:memory')

    def test_should_have_no_effect_for_an_absent_or_already_deleted_memory(
        self,
    ) -> None:
        self.memories.find_by_id_for_update.return_value = None

        self.subject.execute('account', 'memory')

        self.changes.erase_by_memory_id.assert_not_called()
        self.memories.remove.assert_not_called()
        self.memories.advance_fence.assert_not_called()

    def test_should_leave_a_foreign_memory_and_its_change_texts_intact(self) -> None:
        # The repository scopes the lookup to the caller, so a foreign id is absent.
        self.memories.find_by_id_for_update.return_value = None

        self.subject.execute('another-account', 'memory')

        self.memories.find_by_id_for_update.assert_called_once_with(
            'another-account', 'memory'
        )
        self.changes.erase_by_memory_id.assert_not_called()
        self.memories.remove.assert_not_called()
        self.memories.advance_fence.assert_not_called()

    def test_should_advance_the_fence_with_the_deletion_time_when_it_is_later(
        self,
    ) -> None:
        self.memories.lock_account.return_value = self.now - timedelta(days=1)

        self.subject.execute('account', 'memory')

        self.memories.advance_fence.assert_called_once_with('account', self.now)

    def test_should_leave_monotonic_fence_handling_to_the_repository(self) -> None:
        self.memories.lock_account.return_value = self.now + timedelta(days=1)

        self.subject.execute('account', 'memory')

        # The repository stores greatest(coalesce(current, at), at), so a clock step
        # backwards cannot move the fence; the use case always offers the current time.
        self.memories.advance_fence.assert_called_once_with('account', self.now)

    def test_should_not_touch_any_repository_when_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'memory')

        self.database.transaction.assert_not_called()
        self.memories.lock_account.assert_not_called()

    def test_should_not_touch_any_repository_when_the_access_revision_changed(
        self,
    ) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'memory')

        self.database.transaction.assert_not_called()
        self.memories.lock_account.assert_not_called()
        self.changes.erase_by_memory_id.assert_not_called()

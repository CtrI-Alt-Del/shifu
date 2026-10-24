from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class RemoveLearnerMemoryUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        access_provider: MentorAccessProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._access_provider: MentorAccessProvider = access_provider
        self._clock_provider = clock_provider

    def execute(self, account_id: str, memory_id: str) -> None:
        """Delete an owned memory idempotently; absent and foreign ids change nothing."""
        grant = self._access_provider.authorize(
            account_id, f'memory:remove:{memory_id}'
        )
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            repositories.learner_memories.lock_account(account_id)
            memory = repositories.learner_memories.find_by_id_for_update(
                account_id, memory_id
            )
            if memory is None:
                return
            repositories.learner_memory_changes.erase_by_memory_id(
                account_id, memory_id
            )
            repositories.learner_memories.remove(account_id, memory_id)
            repositories.learner_memories.advance_fence(
                account_id, self._clock_provider.now()
            )

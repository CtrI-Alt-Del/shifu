from shifu.intelligence.core.interfaces import IntelligenceDatabase


class PurgeLearnerMemoriesForAccountUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> int:
        """Remove every memory datum of the account; repeated calls return 0."""
        with self._database.transaction() as repositories:
            # Serialize with any analysis, edit or delete that already passed its
            # access check, so none can commit after the purge.
            repositories.learner_memories.lock_account(account_id)
            changes = repositories.learner_memory_changes.remove_by_account_id(
                account_id
            )
            memories = repositories.learner_memories.remove_by_account_id(account_id)
        return changes + memories

from shifu.intelligence.core.domain.structures import (
    LearnerMemoryDetails,
    LearnerMemoryFilter,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import MentorAccessProvider


class ListLearnerMemoriesUseCase:
    def __init__(
        self, database: IntelligenceDatabase, access_provider: MentorAccessProvider
    ) -> None:
        self._database = database
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, filter: LearnerMemoryFilter
    ) -> tuple[LearnerMemoryDetails, ...]:
        grant = self._access_provider.authorize(account_id, 'memory:list')
        self._access_provider.assert_current(grant)
        normalized = LearnerMemoryFilter(
            query=filter.query or None, category=filter.category
        )
        with self._database.transaction() as repositories:
            return repositories.learner_memories.find_many(account_id, normalized)

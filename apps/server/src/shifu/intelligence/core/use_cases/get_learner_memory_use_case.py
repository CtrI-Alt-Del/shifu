from shifu.intelligence.core.domain.errors import LearnerMemoryNotFoundError
from shifu.intelligence.core.domain.structures import LearnerMemoryDetails
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import MentorAccessProvider


class GetLearnerMemoryUseCase:
    def __init__(
        self, database: IntelligenceDatabase, access_provider: MentorAccessProvider
    ) -> None:
        self._database = database
        self._access_provider: MentorAccessProvider = access_provider

    def execute(self, account_id: str, memory_id: str) -> LearnerMemoryDetails:
        grant = self._access_provider.authorize(account_id, f'memory:read:{memory_id}')
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            details = repositories.learner_memories.find_details(account_id, memory_id)
        if details is None:
            raise LearnerMemoryNotFoundError
        return details

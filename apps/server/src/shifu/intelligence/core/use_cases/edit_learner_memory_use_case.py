from shifu.intelligence.core.domain.entities import LearnerMemory
from shifu.intelligence.core.domain.errors import (
    LearnerMemoryContentInvalidError,
    LearnerMemoryNotFoundError,
)
from shifu.intelligence.core.domain.structures import LearnerMemoryDetails
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    LearnerMemoryAnalyzerProvider,
)
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class EditLearnerMemoryUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        analyzer: LearnerMemoryAnalyzerProvider,
        access_provider: MentorAccessProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._database = database
        self._analyzer = analyzer
        self._access_provider: MentorAccessProvider = access_provider
        self._clock_provider = clock_provider

    def execute(
        self, account_id: str, memory_id: str, content: str, expected_version: int
    ) -> LearnerMemoryDetails:
        grant = self._access_provider.authorize(account_id, f'memory:edit:{memory_id}')
        self._access_provider.assert_current(grant)
        cleaned = content.strip()
        if not 1 <= len(cleaned) <= LearnerMemory.MAX_CONTENT_CODE_POINTS:
            raise LearnerMemoryContentInvalidError
        # Compute concepts before locking: a first lazy spaCy load must not hold the
        # account lock that serializes analysis and deletion.
        concepts = self._analyzer.concepts(cleaned)
        with self._database.transaction() as repositories:
            repositories.learner_memories.lock_account(account_id)
            memory = repositories.learner_memories.find_by_id_for_update(
                account_id, memory_id
            )
            if memory is None:
                raise LearnerMemoryNotFoundError
            memory.edit(content, expected_version, self._clock_provider.now())
            repositories.learner_memories.update(memory, concepts)
            details = repositories.learner_memories.find_details(account_id, memory_id)
        if details is None:
            raise LearnerMemoryNotFoundError
        return details

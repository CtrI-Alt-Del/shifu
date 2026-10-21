from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.core.domain.structures.mentor_intent_match import (
    MentorIntentMatch,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)


class EmbeddingsMentorIntentClassifierProvider:
    _repository: MentorEmbeddingsRepository
    _resources: MentorResources

    def __init__(
        self, repository: MentorEmbeddingsRepository, resources: MentorResources
    ) -> None:
        self._repository = repository
        self._resources = resources

    def classify(self, query: tuple[float, ...]) -> tuple[MentorIntentMatch, ...]:
        # All labels have an independent gate. Global top-K would lose a second intent.
        matches = self._repository.find_nearest(
            'intents', self._resources.version, query, tuple(self._resources.intents)
        )
        maximum: dict[str, float] = {}
        for match in matches:
            maximum[match.reference_id] = max(
                maximum.get(match.reference_id, -1), match.similarity
            )
        # Iterate only trusted corpus labels: unknown repository IDs cannot become intents.
        return tuple(
            MentorIntentMatch(intent=MentorIntent(label), similarity=maximum[label])
            for label in self._resources.intents
            if maximum.get(label, -1)
            >= self._resources.manifest.intent_thresholds[label]
        )

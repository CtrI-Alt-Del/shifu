from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.core.domain.structures.mentor_intent_match import (
    MentorIntentMatch,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)
from shifu.intelligence.providers.intent_classification.lexical.lexical_mentor_action_request_provider import (
    LexicalMentorActionRequestProvider,
)


class EmbeddingsMentorIntentClassifierProvider:
    _ACTION_INTENTS = frozenset({MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL})
    _repository: MentorEmbeddingsRepository
    _resources: MentorResources
    _actions: LexicalMentorActionRequestProvider

    def __init__(
        self,
        repository: MentorEmbeddingsRepository,
        resources: MentorResources,
        actions: LexicalMentorActionRequestProvider | None = None,
    ) -> None:
        self._repository = repository
        self._resources = resources
        self._actions = actions or LexicalMentorActionRequestProvider()

    def classify(
        self, query: tuple[float, ...], text: str
    ) -> tuple[MentorIntentMatch, ...]:
        # All labels have an independent gate. Global top-K would lose a second intent.
        matches = self._repository.find_nearest(
            'intents', self._resources.version, query, tuple(self._resources.intents)
        )
        maximum: dict[str, float] = {}
        for match in matches:
            maximum[match.reference_id] = max(
                maximum.get(match.reference_id, -1), match.similarity
            )
        # An action intent also needs an explicit lexical request in the text.
        explicit = self._actions.explicit_intents(text)
        # Iterate only trusted corpus labels: unknown repository IDs cannot become intents.
        return tuple(
            MentorIntentMatch(intent=MentorIntent(label), similarity=maximum[label])
            for label in self._resources.intents
            if maximum.get(label, -1)
            >= self._resources.manifest.intent_thresholds[label]
            and (
                MentorIntent(label) not in self._ACTION_INTENTS
                or MentorIntent(label) in explicit
            )
        )

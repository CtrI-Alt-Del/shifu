"""Compose module-owned Mentor ports without importing private repositories."""

from threading import Lock
from typing import TYPE_CHECKING

from shifu.intelligence.core.domain.structures import (
    MentorRouteResult,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    MentorEmbeddingsProvider,
    MentorTelemetryProvider,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.interfaces import MentorCatalogProvider

if TYPE_CHECKING:
    from shifu.intelligence.core.interfaces import MentorRouteProvider
    from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
        SpacyMentorTextPreprocessorProvider,
    )


class LazyMentorRouteProvider:
    """Load installed local resources once; never prepare indexes in a request.

    The spaCy preprocessor and the embeddings provider may be injected so the Mentor
    summarizer and the router share one loaded copy of each local model.
    """

    def __init__(
        self,
        database: IntelligenceDatabase,
        catalog: MentorCatalogProvider,
        telemetry: MentorTelemetryProvider | None = None,
        *,
        preprocessor: 'SpacyMentorTextPreprocessorProvider | None' = None,
        embeddings: MentorEmbeddingsProvider | None = None,
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._catalog: MentorCatalogProvider = catalog
        self._preprocessor: SpacyMentorTextPreprocessorProvider | None = preprocessor
        self._embeddings: MentorEmbeddingsProvider | None = embeddings
        self._provider: MentorRouteProvider | None = None
        self._lock: Lock = Lock()
        self._telemetry: MentorTelemetryProvider = telemetry or (
            LangfuseMentorTelemetryProvider()
        )
        self._catalog_version: str | None = None

    def route(
        self,
        content: str,
        context: MentorContextSnapshot,
        topics: tuple[str, ...] = (),
    ) -> MentorRouteResult:
        from shifu.intelligence.ai.data.mentor_resources import MentorResources

        with self._lock:
            resources = MentorResources()
            resources.bind_catalog_version(self._catalog.read_projection())
            if (
                self._catalog_version is not None
                and resources.version != self._catalog_version
            ):
                raise ServiceUnavailableError(
                    'O índice local do Mentor precisa ser atualizado.'
                )
            if self._provider is None:
                from shifu.intelligence.database.mentor_embeddings_database_repository import (
                    MentorEmbeddingsDatabaseRepository,
                )
                from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
                    SentenceTransformersEmbeddingsProvider,
                )
                from shifu.intelligence.providers.retrieval.sentence_transformers.sentence_transformers_mentor_faq_reranker_provider import (
                    SentenceTransformersMentorFaqRerankerProvider,
                )
                from shifu.intelligence.providers.routing.local_mentor_route_provider import (
                    LocalMentorRouteProvider,
                )
                from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
                    SpacyMentorTextPreprocessorProvider,
                )

                try:
                    embeddings = self._embeddings or (
                        SentenceTransformersEmbeddingsProvider()
                    )
                    preprocessor = self._preprocessor or (
                        SpacyMentorTextPreprocessorProvider()
                    )
                    # Injected providers may defer loading; force it here so a missing
                    # local model still fails closed before any request is routed.
                    embeddings.embed_queries(())
                    preprocessor.tokenize('')
                    self._provider = LocalMentorRouteProvider(
                        embeddings,
                        MentorEmbeddingsDatabaseRepository(self._database),
                        preprocessor,
                        resources,
                        telemetry=self._telemetry,
                        catalog_provider=self._catalog,
                        reranker_provider=SentenceTransformersMentorFaqRerankerProvider(),
                    )
                    self._catalog_version = resources.version
                except (OSError, ValueError) as error:
                    raise ServiceUnavailableError(
                        'O índice local do Mentor está indisponível.'
                    ) from error
            return self._provider.route(content, context, topics)

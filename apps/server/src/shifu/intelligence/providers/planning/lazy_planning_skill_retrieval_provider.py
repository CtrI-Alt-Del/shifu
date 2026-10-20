"""Compose the Planner retrieval once per process from installed local resources."""

from threading import Lock
from typing import TYPE_CHECKING

from shifu.intelligence.core.domain.errors.planning_index_unavailable_error import (
    PlanningIndexUnavailableError,
)
from shifu.intelligence.core.domain.structures.planning_query import PlanningQuery
from shifu.intelligence.core.domain.structures.planning_skill_ranking import (
    PlanningSkillRanking,
)
from shifu.intelligence.core.interfaces.intelligence_database import (
    IntelligenceDatabase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces.curriculum_catalog_provider import (
    CurriculumCatalogProvider,
)

if TYPE_CHECKING:
    from shifu.intelligence.core.interfaces.planning_skill_retrieval_provider import (
        PlanningSkillRetrievalProvider,
    )


class LazyPlanningSkillRetrievalProvider:
    """Load the active index lazily; never prepare an index inside a request."""

    def __init__(
        self, database: IntelligenceDatabase, catalog: CurriculumCatalogProvider
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._catalog: CurriculumCatalogProvider = catalog
        self._provider: PlanningSkillRetrievalProvider | None = None
        self._version: str | None = None
        self._lock: Lock = Lock()

    def retrieve(self, query: PlanningQuery) -> PlanningSkillRanking:
        from shifu.intelligence.ai.data.planner_resources import PlannerResources

        with self._lock:
            resources = PlannerResources()
            skills = self._catalog.list_skills()
            resources.bind_catalog(skills)
            if self._provider is None or self._version != resources.version:
                from shifu.intelligence.database.planning_embeddings_database_repository import (
                    PlanningEmbeddingsDatabaseRepository,
                )
                from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
                    SentenceTransformersEmbeddingsProvider,
                )
                from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_sentence_transformers_planning_skill_retrieval_provider import (
                    TfidfSentenceTransformersPlanningSkillRetrievalProvider,
                )
                from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
                    SpacyPlanningTextPreprocessorProvider,
                )

                repository = PlanningEmbeddingsDatabaseRepository(self._database)
                # A stale index never matches new catalog text against old vectors.
                if repository.find_active_version() != resources.version:
                    raise PlanningIndexUnavailableError
                try:
                    self._provider = (
                        TfidfSentenceTransformersPlanningSkillRetrievalProvider(
                            skills,
                            SentenceTransformersEmbeddingsProvider(),
                            repository,
                            SpacyPlanningTextPreprocessorProvider(
                                resources.manifest.negation
                            ),
                            resources,
                        )
                    )
                except (OSError, ValueError, ServiceUnavailableError) as error:
                    raise PlanningIndexUnavailableError from error
                self._version = resources.version
            return self._provider.retrieve(query)

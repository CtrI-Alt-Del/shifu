"""Compose the Planner retrieval once per process from installed local resources."""

from threading import Lock
from typing import TYPE_CHECKING, Literal

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
    from shifu.intelligence.ai.data.planner_resources import PlannerResources
    from shifu.intelligence.core.interfaces.planning_skill_retrieval_provider import (
        PlanningSkillRetrievalProvider,
    )
    from shifu.intelligence.core.interfaces.planning_word_vectors_provider import (
        PlanningWordVectorsProvider,
    )
    from shifu.shared.core.domain.structures.skill_catalog_entry import (
        SkillCatalogEntry,
    )

PlanningSemanticModel = Literal['word2vec', 'e5']


class LazyPlanningSkillRetrievalProvider:
    """Load the search lazily; never download a model inside a request.

    With Word2Vec the Skill vectors are averages computed in memory, so a catalog
    change only rebuilds them. With e5 they come from the prepared index, and a
    stale index fails closed instead of matching new text against old vectors.
    """

    def __init__(
        self,
        database: IntelligenceDatabase,
        catalog: CurriculumCatalogProvider,
        semantic_model: PlanningSemanticModel = 'word2vec',
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._catalog: CurriculumCatalogProvider = catalog
        self._semantic_model: PlanningSemanticModel = semantic_model
        self._provider: PlanningSkillRetrievalProvider | None = None
        self._word_vectors: PlanningWordVectorsProvider | None = None
        self._version: str | None = None
        self._lock: Lock = Lock()

    def retrieve(self, query: PlanningQuery) -> PlanningSkillRanking:
        from shifu.intelligence.ai.data.planner_resources import PlannerResources

        with self._lock:
            resources = PlannerResources()
            skills = self._catalog.list_skills()
            resources.bind_catalog(skills)
            if self._provider is None or self._version != resources.version:
                try:
                    self._provider = (
                        self._build_word2vec(skills, resources)
                        if self._semantic_model == 'word2vec'
                        else self._build_e5(skills, resources)
                    )
                except (OSError, ValueError, ServiceUnavailableError) as error:
                    raise PlanningIndexUnavailableError from error
                self._version = resources.version
            return self._provider.retrieve(query)

    def _build_word2vec(
        self, skills: 'tuple[SkillCatalogEntry, ...]', resources: 'PlannerResources'
    ) -> 'PlanningSkillRetrievalProvider':
        from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_word2vec_planning_skill_retrieval_provider import (
            TfidfWord2VecPlanningSkillRetrievalProvider,
        )
        from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
            SpacyPlanningTextPreprocessorProvider,
        )
        from shifu.intelligence.providers.planning.word_vectors.huggingface.nilc_word2vec_word_vectors_provider import (
            NilcWord2VecWordVectorsProvider,
        )

        # The word vectors do not depend on the catalog; load them once.
        if self._word_vectors is None:
            self._word_vectors = NilcWord2VecWordVectorsProvider()
        return TfidfWord2VecPlanningSkillRetrievalProvider(
            skills,
            self._word_vectors,
            SpacyPlanningTextPreprocessorProvider(resources.manifest.negation),
            resources,
        )

    def _build_e5(
        self, skills: 'tuple[SkillCatalogEntry, ...]', resources: 'PlannerResources'
    ) -> 'PlanningSkillRetrievalProvider':
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
        return TfidfSentenceTransformersPlanningSkillRetrievalProvider(
            skills,
            SentenceTransformersEmbeddingsProvider(),
            repository,
            SpacyPlanningTextPreprocessorProvider(resources.manifest.negation),
            resources,
        )

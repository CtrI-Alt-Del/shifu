import numpy as np
from numpy.typing import NDArray

from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.structures.planning_query import PlanningQuery
from shifu.intelligence.core.domain.structures.planning_skill_rank_entry import (
    PlanningSkillRankEntry,
)
from shifu.intelligence.core.domain.structures.planning_skill_ranking import (
    PlanningSkillRanking,
)
from shifu.intelligence.core.interfaces.planning_text_preprocessor_provider import (
    PlanningTextPreprocessorProvider,
)
from shifu.intelligence.core.interfaces.planning_word_vectors_provider import (
    PlanningWordVectorsProvider,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_index import (
    TfidfIndex,
)
from shifu.shared.core.domain.structures.skill_catalog_entry import SkillCatalogEntry


class TfidfWord2VecPlanningSkillRetrievalProvider:
    """Hybrid Skill search: a TF-IDF ranking and a Word2Vec ranking, fused by RRF.

    A text becomes the TF-IDF weighted average of the Word2Vec vectors of its
    words, so rare and specific words pull the meaning more than common ones. The
    lexical ranking matches lemmas; the vectors use the words as written, because
    the Word2Vec vocabulary holds inflected forms and a wrong lemma loses the word.
    Everything lives in memory: the catalog is small and an average is cheap.
    """

    _skill_ids: tuple[str, ...]
    _index: TfidfIndex
    _word_index: TfidfIndex
    _word_vectors: PlanningWordVectorsProvider
    _preprocessor: PlanningTextPreprocessorProvider
    _resources: PlannerResources
    _negations: frozenset[str]
    _skill_vectors: NDArray[np.float64]

    def __init__(
        self,
        skills: tuple[SkillCatalogEntry, ...],
        word_vectors: PlanningWordVectorsProvider,
        preprocessor: PlanningTextPreprocessorProvider,
        resources: PlannerResources,
    ) -> None:
        if not skills or len({skill.id for skill in skills}) != len(skills):
            raise ValueError('Planner retrieval needs a non-empty unique catalog')
        self._skill_ids = tuple(skill.id for skill in skills)
        self._word_vectors = word_vectors
        self._preprocessor = preprocessor
        self._resources = resources
        # A word average cannot express "not X"; negations are left to TF-IDF.
        self._negations = frozenset(resources.manifest.negation)
        texts = [f'{skill.name} {skill.description}' for skill in skills]
        self._index = TfidfIndex(
            [list(preprocessor.lexical_tokens(text)) for text in texts]
        )
        words = [list(preprocessor.word_tokens(text)) for text in texts]
        self._word_index = TfidfIndex(words)
        self._skill_vectors = np.array(
            [self._average(document) for document in words], dtype=np.float64
        )

    def retrieve(self, query: PlanningQuery) -> PlanningSkillRanking:
        manifest = self._resources.manifest
        text = self._query_text(query)
        tokens = list(self._preprocessor.lexical_tokens(text))
        lexical = self._lexical_ranking(tokens, manifest.lexical_limit)
        words = list(self._preprocessor.word_tokens(text))
        semantic = tuple(
            skill_id
            for skill_id, _ in self._semantic_ranking(words)[: manifest.semantic_limit]
        )
        fused: dict[str, float] = {}
        lexical_ranks = {skill_id: rank for rank, skill_id in enumerate(lexical, 1)}
        semantic_ranks = {skill_id: rank for rank, skill_id in enumerate(semantic, 1)}
        for ranks in (lexical_ranks, semantic_ranks):
            for skill_id, rank in ranks.items():
                fused[skill_id] = fused.get(skill_id, 0.0) + 1 / (manifest.rrf_k + rank)
        ordered = sorted(fused, key=lambda skill_id: (-fused[skill_id], skill_id))
        return PlanningSkillRanking(
            index_version=self._resources.version,
            lexical_ranking=lexical,
            semantic_ranking=semantic,
            entries=tuple(
                PlanningSkillRankEntry(
                    skill_id=skill_id,
                    score=fused[skill_id],
                    lexical_rank=lexical_ranks.get(skill_id),
                    semantic_rank=semantic_ranks.get(skill_id),
                )
                for skill_id in ordered[: manifest.candidate_limit]
            ),
        )

    def similarities(self, query: PlanningQuery) -> tuple[tuple[str, float], ...]:
        """Cosine between the query and every Skill, most similar first."""
        words = list(self._preprocessor.word_tokens(self._query_text(query)))
        return self._semantic_ranking(words)

    def _query_text(self, query: PlanningQuery) -> str:
        return self._preprocessor.normalize(' '.join((query.intent, *query.answers)))

    def _lexical_ranking(self, tokens: list[str], limit: int) -> tuple[str, ...]:
        scores = self._index.scores(tokens)
        ranked = sorted(
            (index for index, score in enumerate(scores) if score > 0),
            key=lambda index: (-scores[index], self._skill_ids[index]),
        )
        return tuple(self._skill_ids[index] for index in ranked[:limit])

    def _semantic_ranking(self, words: list[str]) -> tuple[tuple[str, float], ...]:
        query = self._average(words)
        if not query.any():
            return ()
        # Both sides are unit vectors, so the dot product is the cosine similarity.
        similarities = self._skill_vectors @ query
        ranked = sorted(
            (
                index
                for index in range(len(self._skill_ids))
                if self._skill_vectors[index].any()
            ),
            key=lambda index: (-similarities[index], self._skill_ids[index]),
        )
        return tuple(
            (self._skill_ids[index], round(float(similarities[index]), 5))
            for index in ranked
        )

    def _average(self, words: list[str]) -> NDArray[np.float64]:
        """TF-IDF weighted average of the known word vectors, scaled to length 1."""
        weights = self._word_index.weights(
            [word for word in words if word not in self._negations]
        )
        vectors = self._word_vectors.vectors_of(tuple(weights))
        total = np.zeros(self._word_vectors.dimension, dtype=np.float64)
        for word, vector in vectors.items():
            total += weights[word] * np.asarray(vector, dtype=np.float64)
        norm = float(np.linalg.norm(total))
        # No known word: a zero vector, which ranks nothing instead of guessing.
        return total / norm if norm > 0 else total

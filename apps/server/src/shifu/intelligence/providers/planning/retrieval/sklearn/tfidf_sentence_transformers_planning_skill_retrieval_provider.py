from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer

from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.errors.planning_index_unavailable_error import (
    PlanningIndexUnavailableError,
)
from shifu.intelligence.core.domain.structures.planning_query import PlanningQuery
from shifu.intelligence.core.domain.structures.planning_skill_rank_entry import (
    PlanningSkillRankEntry,
)
from shifu.intelligence.core.domain.structures.planning_skill_ranking import (
    PlanningSkillRanking,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_provider import (
    MentorEmbeddingsProvider,
)
from shifu.intelligence.core.interfaces.planning_embeddings_repository import (
    PlanningEmbeddingsRepository,
)
from shifu.intelligence.core.interfaces.planning_text_preprocessor_provider import (
    PlanningTextPreprocessorProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures.skill_catalog_entry import SkillCatalogEntry


def _identity(tokens: list[str]) -> list[str]:
    return tokens


class _SparseMatrix(Protocol):
    """The scipy sparse surface this adapter relies on."""

    @property
    def T(self) -> '_SparseMatrix': ...  # noqa: N802 - scipy attribute name.
    def __matmul__(self, other: '_SparseMatrix') -> '_SparseMatrix': ...
    def toarray(self) -> NDArray[np.float64]: ...


class _TfidfIndex:
    """Contain the untyped scikit-learn surface behind a typed cosine scorer."""

    _vectorizer: TfidfVectorizer
    _matrix: _SparseMatrix

    def __init__(self, documents: list[list[str]]) -> None:
        # scikit-learn accepts a callable analyzer; Pyright infers the string default.
        self._vectorizer = TfidfVectorizer(
            analyzer=_identity,  # pyright: ignore[reportArgumentType]
            norm='l2',
        )
        self._matrix = cast('_SparseMatrix', self._vectorizer.fit_transform(documents))  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no type information.

    def scores(self, tokens: list[str]) -> list[float]:
        if not tokens:
            return []
        query = cast(
            '_SparseMatrix',
            self._vectorizer.transform([tokens]),  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no type information.
        )
        # Both sides are L2-normalized, so the dot product is the cosine similarity.
        return [float(value) for value in (self._matrix @ query.T).toarray().ravel()]


class TfidfSentenceTransformersPlanningSkillRetrievalProvider:
    _skill_ids: tuple[str, ...]
    _index: _TfidfIndex
    _embeddings: MentorEmbeddingsProvider
    _repository: PlanningEmbeddingsRepository
    _preprocessor: PlanningTextPreprocessorProvider
    _resources: PlannerResources

    def __init__(
        self,
        skills: tuple[SkillCatalogEntry, ...],
        embeddings: MentorEmbeddingsProvider,
        repository: PlanningEmbeddingsRepository,
        preprocessor: PlanningTextPreprocessorProvider,
        resources: PlannerResources,
    ) -> None:
        if not skills or len({skill.id for skill in skills}) != len(skills):
            raise ValueError('Planner retrieval needs a non-empty unique catalog')
        self._skill_ids = tuple(skill.id for skill in skills)
        self._embeddings = embeddings
        self._repository = repository
        self._preprocessor = preprocessor
        self._resources = resources
        # The lexical corpus is fitted once per process from authorized Skill text only.
        self._index = _TfidfIndex(
            [
                list(preprocessor.lexical_tokens(f'{skill.name} {skill.description}'))
                for skill in skills
            ]
        )

    def retrieve(self, query: PlanningQuery) -> PlanningSkillRanking:
        manifest = self._resources.manifest
        text = self._preprocessor.normalize(' '.join((query.intent, *query.answers)))
        lexical = self._lexical_ranking(text, manifest.lexical_limit)
        try:
            vector = self._embeddings.embed_queries((text,))[0]
            matches = self._repository.find_nearest(
                self._resources.version,
                vector,
                self._skill_ids,
                manifest.semantic_limit,
            )
        except (ServiceUnavailableError, ValueError) as error:
            raise PlanningIndexUnavailableError from error
        semantic = tuple(dict.fromkeys(match.skill_id for match in matches))
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

    def _lexical_ranking(self, text: str, limit: int) -> tuple[str, ...]:
        scores = self._index.scores(list(self._preprocessor.lexical_tokens(text)))
        ranked = sorted(
            (index for index, score in enumerate(scores) if score > 0),
            key=lambda index: (-scores[index], self._skill_ids[index]),
        )
        return tuple(self._skill_ids[index] for index in ranked[:limit])

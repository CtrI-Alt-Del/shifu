from __future__ import annotations

import math

import pytest

from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.errors import PlanningIndexUnavailableError
from shifu.intelligence.core.domain.structures import PlanningQuery
from shifu.intelligence.providers.planning import (
    lazy_planning_skill_retrieval_provider as lazy_module,
)
from shifu.intelligence.providers.planning.lazy_planning_skill_retrieval_provider import (
    LazyPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_index import (
    TfidfIndex,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_word2vec_planning_skill_retrieval_provider import (
    TfidfWord2VecPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.word_vectors.huggingface import (
    nilc_word2vec_word_vectors_provider as nilc_module,
)
from shifu.intelligence.providers.planning.word_vectors.huggingface.nilc_word2vec_word_vectors_provider import (
    NilcWord2VecWordVectorsProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures.skill_catalog_entry import SkillCatalogEntry

# Three directions of meaning: web back end, web front end and cooking.
_VECTORS: dict[str, tuple[float, ...]] = {
    'django': (1.0, 0.0, 0.0),
    'python': (0.9, 0.1, 0.0),
    'servidor': (0.8, 0.2, 0.0),
    'framework': (0.6, 0.4, 0.0),
    'react': (0.0, 1.0, 0.0),
    'componente': (0.1, 0.9, 0.0),
    'tela': (0.0, 0.8, 0.0),
    'receita': (0.0, 0.0, 1.0),
    'cozinhar': (0.0, 0.1, 0.9),
}
_SKILLS = (
    SkillCatalogEntry(id='django', name='Django', description='python servidor'),
    SkillCatalogEntry(id='react', name='React', description='componente tela'),
)


class _FakeWordVectors:
    dimension = 3

    def vectors_of(self, words: tuple[str, ...]) -> dict[str, tuple[float, ...]]:
        return {word: _VECTORS[word] for word in words if word in _VECTORS}


class _WhitespacePreprocessor:
    def normalize(self, text: str) -> str:
        return ' '.join(text.split())

    def lexical_tokens(self, text: str) -> tuple[str, ...]:
        return tuple(text.lower().split())

    def word_tokens(self, text: str) -> tuple[str, ...]:
        return tuple(text.lower().split())


def _provider() -> TfidfWord2VecPlanningSkillRetrievalProvider:
    return TfidfWord2VecPlanningSkillRetrievalProvider(
        _SKILLS, _FakeWordVectors(), _WhitespacePreprocessor(), PlannerResources()
    )


class TestTfidfIndexWeights:
    def test_should_multiply_the_count_by_the_smoothed_idf(self) -> None:
        index = TfidfIndex([['python', 'web'], ['react', 'web']])

        weights = index.weights(['python', 'python', 'web', 'cozinhar'])

        # idf = ln((1 + n) / (1 + df)) + 1 with n = 2 documents.
        assert weights['python'] == pytest.approx(2 * (math.log(3 / 2) + 1))
        assert weights['web'] == pytest.approx(math.log(3 / 3) + 1)
        assert weights['cozinhar'] == pytest.approx(math.log(3) + 1)
        assert weights['cozinhar'] > weights['python'] / 2 > weights['web']


class TestTfidfWord2VecPlanningSkillRetrievalProvider:
    def test_should_find_a_skill_by_meaning_without_a_shared_word(self) -> None:
        provider = _provider()

        ranking = provider.retrieve(
            PlanningQuery(intent='framework servidor', answers=())
        )

        assert ranking.lexical_ranking == ('django',)
        assert ranking.semantic_ranking[0] == 'django'
        assert provider.similarities(PlanningQuery(intent='tela bonita', answers=()))[
            0
        ][0] == ('react')

    def test_should_rank_by_meaning_when_no_word_matches_the_catalog(self) -> None:
        ranking = _provider().retrieve(
            PlanningQuery(intent='framework python', answers=('tela',))
        )

        assert ranking.semantic_ranking == ('django', 'react')
        assert ranking.entries[0].skill_id == 'django'

    def test_should_keep_an_uncovered_query_far_from_every_skill(self) -> None:
        provider = _provider()

        covered = provider.similarities(PlanningQuery(intent='django', answers=()))
        uncovered = provider.similarities(
            PlanningQuery(intent='cozinhar receita', answers=())
        )

        assert uncovered[0][1] < 0.2 < covered[0][1]

    def test_should_rank_nothing_by_meaning_without_a_known_word(self) -> None:
        provider = _provider()

        ranking = provider.retrieve(PlanningQuery(intent='react xyz', answers=()))

        assert provider.similarities(PlanningQuery(intent='xyz', answers=())) == ()
        assert ranking.lexical_ranking == ('react',)

    def test_should_leave_negations_out_of_the_meaning_average(self) -> None:
        provider = _provider()

        with_negation = provider.similarities(
            PlanningQuery(intent='não react', answers=())
        )
        without_negation = provider.similarities(
            PlanningQuery(intent='react', answers=())
        )

        assert with_negation == without_negation

    def test_should_require_a_unique_non_empty_catalog(self) -> None:
        with pytest.raises(ValueError, match='non-empty unique catalog'):
            TfidfWord2VecPlanningSkillRetrievalProvider(
                (), _FakeWordVectors(), _WhitespacePreprocessor(), PlannerResources()
            )


class TestNilcWord2VecWordVectorsProvider:
    def test_should_fail_closed_when_the_files_were_not_prepared(
        self, tmp_path: object
    ) -> None:
        with pytest.raises(ServiceUnavailableError):
            NilcWord2VecWordVectorsProvider(cache_folder=str(tmp_path))


class _FakeCatalog:
    def list_skills(self) -> tuple[SkillCatalogEntry, ...]:
        return _SKILLS


class TestLazyPlanningSkillRetrievalProvider:
    def test_should_search_with_word2vec_without_a_prepared_index(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            nilc_module,
            'NilcWord2VecWordVectorsProvider',
            lambda: _FakeWordVectors(),
        )
        provider = LazyPlanningSkillRetrievalProvider(
            database=object(),  # pyright: ignore[reportArgumentType] - never touched.
            catalog=_FakeCatalog(),  # pyright: ignore[reportArgumentType]
            semantic_model='word2vec',
        )

        ranking = provider.retrieve(
            PlanningQuery(intent='quero aprender python', answers=())
        )

        assert ranking.entries[0].skill_id == 'django'

    def test_should_fail_closed_when_the_word_vectors_are_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def missing() -> object:
            raise ServiceUnavailableError('missing')

        monkeypatch.setattr(nilc_module, 'NilcWord2VecWordVectorsProvider', missing)
        provider = lazy_module.LazyPlanningSkillRetrievalProvider(
            database=object(),  # pyright: ignore[reportArgumentType] - never touched.
            catalog=_FakeCatalog(),  # pyright: ignore[reportArgumentType]
        )

        with pytest.raises(PlanningIndexUnavailableError):
            provider.retrieve(PlanningQuery(intent='python', answers=()))

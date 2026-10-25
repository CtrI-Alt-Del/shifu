"""Labeled pt-BR evaluation of the Planner classification and retrieval (CI-03)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.intelligence.ai.data import planner_resources as planner_resources_module
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.enums import PlanningIntentKind
from shifu.intelligence.core.domain.errors import (
    PlanningClassificationUnavailableError,
    PlanningIndexUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningIndexedEmbedding,
    PlanningQuery,
    PlanningSkillRanking,
)
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PLANNING_EMBEDDING_DIMENSION,
)
from shifu.intelligence.core.use_cases import (
    ClassifyPlanningIntentUseCase,
    RetrievePlanningSkillsUseCase,
)
from shifu.intelligence.database.planning_embeddings_database_repository import (
    PlanningEmbeddingsDatabaseRepository,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.database.sqlalchemy.models import (
    PlanningEmbeddingVersionModel,
    PlanningSkillEmbeddingModel,
)
from shifu.intelligence.prepare_planning_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.planning.intent_classification.openrouter import (
    jev_planning_intent_classifier_provider as jev_module,
)
from shifu.intelligence.providers.planning.intent_classification.openrouter.jev_planning_intent_classifier_provider import (
    JevPlanningIntentClassifierProvider,
)
from shifu.intelligence.providers.planning.lazy_planning_skill_retrieval_provider import (
    LazyPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_sentence_transformers_planning_skill_retrieval_provider import (
    TfidfSentenceTransformersPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
    SpacyPlanningTextPreprocessorProvider,
)
from shifu.shared.database.seed_data import build_development_seed

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from sqlalchemy import Engine

    from tests.fixtures.postgres_fixture import PostgresDatabase

_DECISIONS_URL = 'https://openrouter.test/api/alpha/decisions'
_MODEL = 'typesafe/jev-1.13'
_KINDS = tuple(kind.value for kind in PlanningIntentKind)


@dataclass(frozen=True)
class _Corpus:
    engine: Engine
    catalog: DatabaseCurriculumCatalogProvider
    database: SqlalchemyIntelligenceDatabase
    repository: PlanningEmbeddingsDatabaseRepository
    ids_by_name: dict[str, str]
    names_by_id: dict[str, str]


@dataclass(frozen=True)
class _Index:
    corpus: _Corpus
    resources: PlannerResources
    version: str
    provider: TfidfSentenceTransformersPlanningSkillRetrievalProvider


@dataclass
class _JevDouble:
    """Transport double of the decisions endpoint keyed by the labeled intent."""

    labels: dict[str, PlanningIntentKind]
    confidence: float = 0.9
    requests: list[dict[str, Any]] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = cast('dict[str, Any]', json.loads(request.content))
        self.requests.append(payload)
        assert request.headers['authorization'] == 'Bearer test-key'
        assert payload['model'] == _MODEL
        assert set(payload['questions']) == {
            JevPlanningIntentClassifierProvider.QUESTION
        }
        question = payload['questions'][JevPlanningIntentClassifierProvider.QUESTION]
        assert question['type'] == 'choice'
        assert set(question['criteria']) == set(_KINDS)
        # Only the current intent and the submitted answers leave the process.
        assert set(payload['state']) == {'intent', 'answers'}
        assert payload['provider'] == {'zdr': True, 'data_collection': 'deny'}
        label = self.labels[payload['state']['intent']]
        return _decision(label.value, self.confidence)


def _decision(choice: str, confidence: float) -> httpx.Response:
    rest = (1 - confidence) / 2
    return httpx.Response(
        200,
        json={
            'answers': {
                JevPlanningIntentClassifierProvider.QUESTION: {
                    'type': 'choice',
                    'choice': choice,
                    'confidence': confidence,
                    'probabilities': {
                        kind: confidence if kind == choice else rest for kind in _KINDS
                    },
                }
            }
        },
    )


def _classifier(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str | None = 'test-key',
) -> JevPlanningIntentClassifierProvider:
    return JevPlanningIntentClassifierProvider(
        httpx.Client(transport=httpx.MockTransport(handler)),
        api_key,
        _DECISIONS_URL,
        _MODEL,
        PlannerResources().manifest.intent_thresholds,
    )


def _evaluate(
    use_case: ClassifyPlanningIntentUseCase,
    items: Iterable[tuple[str, PlanningIntentKind]],
) -> tuple[Counter[tuple[str, str]], float, int]:
    matrix: Counter[tuple[str, str]] = Counter()
    total = correct = undue_refusals = 0
    for text, label in items:
        predicted = use_case.execute(PlanningQuery(intent=text)).kind
        matrix[label.value, predicted.value] += 1
        total += 1
        correct += predicted is label
        undue_refusals += (
            label is PlanningIntentKind.LEARNING
            and predicted is PlanningIntentKind.OUT_OF_SCOPE
        )
    return matrix, correct / total, undue_refusals


def _print_matrix(title: str, matrix: Counter[tuple[str, str]]) -> None:
    print(f'\n[{title}] confusion matrix (rows: expected, columns: predicted)')
    print(f'{"":<14}' + ''.join(f'{kind:>14}' for kind in _KINDS))
    for expected in _KINDS:
        print(
            f'{expected:<14}'
            + ''.join(f'{matrix[expected, predicted]:>14}' for predicted in _KINDS)
        )


def _query(intent: str, answers: Sequence[str] = ()) -> PlanningQuery:
    return PlanningQuery(intent=intent, answers=tuple(answers))


def _names(index: _Index, skill_ids: Iterable[str]) -> list[str]:
    return [index.corpus.names_by_id[skill_id] for skill_id in skill_ids]


def _entry_names(index: _Index, ranking: PlanningSkillRanking) -> list[str]:
    return _names(index, (entry.skill_id for entry in ranking.entries))


def _no_sleep(_seconds: float) -> None:
    return None


def _axis(position: int) -> tuple[float, ...]:
    vector = [0.0] * PLANNING_EMBEDDING_DIMENSION
    vector[position] = 1.0
    return tuple(vector)


@pytest.fixture(scope='module')
def embeddings() -> SentenceTransformersEmbeddingsProvider:
    return SentenceTransformersEmbeddingsProvider()


@pytest.fixture(scope='module')
def preprocessor() -> SpacyPlanningTextPreprocessorProvider:
    return SpacyPlanningTextPreprocessorProvider(PlannerResources().manifest.negation)


@pytest.fixture
def corpus(postgres_database: PostgresDatabase) -> _Corpus:
    seed = build_development_seed()
    curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
    catalog = DatabaseCurriculumCatalogProvider(curriculum)
    database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
    skills = catalog.list_skills()
    return _Corpus(
        engine=postgres_database.engine,
        catalog=catalog,
        database=database,
        repository=PlanningEmbeddingsDatabaseRepository(database),
        ids_by_name={skill.name: skill.id for skill in skills},
        names_by_id={skill.id: skill.name for skill in skills},
    )


@pytest.fixture
def index(
    corpus: _Corpus,
    embeddings: SentenceTransformersEmbeddingsProvider,
    preprocessor: SpacyPlanningTextPreprocessorProvider,
) -> _Index:
    resources = PlannerResources()
    version = prepare_indexes(
        embeddings, corpus.repository, corpus.catalog, resources, preprocessor
    )
    provider = TfidfSentenceTransformersPlanningSkillRetrievalProvider(
        corpus.catalog.list_skills(),
        embeddings,
        corpus.repository,
        preprocessor,
        resources,
    )
    return _Index(corpus, resources, version, provider)


class TestPlanningTextRepresentations:
    def test_should_lemmatize_drop_stop_words_and_keep_negation(
        self, preprocessor: SpacyPlanningTextPreprocessorProvider
    ) -> None:
        tokens = preprocessor.lexical_tokens(
            'Não quero front-end, prefiro APIs e bancos de dados'
        )

        assert tokens[0] == 'não'
        assert 'front-end' in tokens
        assert 'banco' in tokens
        assert 'dado' in tokens
        assert not {'bancos', 'dados', 'e', 'de', 'quero', ','} & set(tokens)
        assert 'nunca' in preprocessor.lexical_tokens(
            'Nunca programei e quero começar pelo básico'
        )
        assert 'nem' in preprocessor.lexical_tokens('Nem web nem interfaces')

    def test_should_keep_the_full_sentence_for_the_semantic_representation(
        self, preprocessor: SpacyPlanningTextPreprocessorProvider
    ) -> None:
        assert (
            preprocessor.normalize('  Não   quero\nfront-end,  prefiro APIs ')
            == 'Não quero front-end, prefiro APIs'
        )

    def test_should_require_negation_tokens_from_the_manifest(self) -> None:
        with pytest.raises(ValueError, match='negation'):
            SpacyPlanningTextPreprocessorProvider(())


class TestPlanningIndexPreparation:
    def test_should_fail_closed_without_an_active_index(
        self,
        corpus: _Corpus,
        embeddings: SentenceTransformersEmbeddingsProvider,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
    ) -> None:
        resources = PlannerResources()
        skills = corpus.catalog.list_skills()
        resources.bind_catalog(skills)
        provider = TfidfSentenceTransformersPlanningSkillRetrievalProvider(
            skills, embeddings, corpus.repository, preprocessor, resources
        )
        query = _query('Quero aprender React')

        with pytest.raises(PlanningIndexUnavailableError):
            provider.retrieve(query)
        with pytest.raises(PlanningIndexUnavailableError):
            LazyPlanningSkillRetrievalProvider(
                corpus.database, corpus.catalog
            ).retrieve(query)
        with pytest.raises(PlanningIndexUnavailableError):
            RetrievePlanningSkillsUseCase(provider, corpus.catalog).execute(query)
        assert corpus.repository.find_active_version() is None

    def test_should_prepare_one_normalized_vector_per_skill_under_one_active_version(
        self,
        index: _Index,
        embeddings: SentenceTransformersEmbeddingsProvider,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
    ) -> None:
        with SqlalchemySession(index.corpus.engine) as session:
            rows = session.execute(
                select(
                    PlanningSkillEmbeddingModel.version,
                    PlanningSkillEmbeddingModel.skill_id,
                    PlanningSkillEmbeddingModel.vector,
                )
            ).all()
            active = session.scalars(
                select(PlanningEmbeddingVersionModel.version).where(
                    PlanningEmbeddingVersionModel.active.is_(True)
                )
            ).all()

        assert {row.skill_id for row in rows} == set(index.corpus.names_by_id)
        assert {row.version for row in rows} == {index.version}
        for row in rows:
            values = [float(value) for value in row.vector]
            assert len(values) == PLANNING_EMBEDDING_DIMENSION
            assert sqrt(sum(value * value for value in values)) == pytest.approx(
                1.0, abs=1e-3
            )
        assert active == [index.version]
        with pytest.raises(ValueError, match='Active immutable index'):
            index.corpus.repository.prepare_version(
                index.version,
                (PlanningIndexedEmbedding(skill_id='skill', vector=_axis(0)),),
            )

        # Promoting another version deactivates the current one atomically.
        index.corpus.repository.prepare_version(
            'older', (PlanningIndexedEmbedding(skill_id='skill', vector=_axis(0)),)
        )
        index.corpus.repository.activate_version('older')
        assert index.corpus.repository.find_active_version() == 'older'
        with pytest.raises(PlanningIndexUnavailableError):
            index.provider.retrieve(_query('Quero aprender React'))

        assert (
            prepare_indexes(
                embeddings,
                index.corpus.repository,
                index.corpus.catalog,
                PlannerResources(),
                preprocessor,
            )
            == index.version
        )
        assert index.corpus.repository.find_active_version() == index.version

    def test_should_prepare_and_activate_the_index_through_the_offline_entry_point(
        self, corpus: _Corpus, postgres_database: PostgresDatabase
    ) -> None:
        environment = dict(os.environ)
        environment['DATABASE_URL'] = postgres_database.url
        completed = subprocess.run(
            [sys.executable, '-m', 'shifu.planning_indexes'],
            cwd=Path(__file__).parents[3],
            env=environment,
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            check=False,
            timeout=900,
        )
        resources = PlannerResources()
        resources.bind_catalog(corpus.catalog.list_skills())

        assert completed.returncode == 0, completed.stderr[-3000:]
        assert f'Planner index activated: {resources.version}' in completed.stdout
        assert corpus.repository.find_active_version() == resources.version

        lazy = LazyPlanningSkillRetrievalProvider(corpus.database, corpus.catalog)
        ranking = lazy.retrieve(_query('Quero aprender React'))

        assert ranking.index_version == resources.version
        assert corpus.names_by_id[ranking.entries[0].skill_id] == 'React'
        assert lazy.retrieve(_query('Quero aprender React')).entries == ranking.entries


class TestPlanningSkillRetrieval:
    def test_should_fuse_lexical_and_semantic_rankings_by_reciprocal_rank(
        self, index: _Index
    ) -> None:
        manifest = index.resources.manifest
        ranking = index.provider.retrieve(
            _query('Quero construir interfaces com componentes e estado usando React')
        )

        assert ranking.index_version == index.version
        assert 0 < len(ranking.lexical_ranking) <= manifest.lexical_limit
        assert 0 < len(ranking.semantic_ranking) <= manifest.semantic_limit
        assert len(ranking.entries) <= manifest.candidate_limit
        expected: dict[str, float] = {}
        for source in (ranking.lexical_ranking, ranking.semantic_ranking):
            for rank, skill_id in enumerate(source, 1):
                expected[skill_id] = expected.get(skill_id, 0.0) + 1 / (
                    manifest.rrf_k + rank
                )
        assert [entry.skill_id for entry in ranking.entries] == sorted(
            expected, key=lambda skill_id: (-expected[skill_id], skill_id)
        )
        for entry in ranking.entries:
            assert entry.score == pytest.approx(expected[entry.skill_id])
            assert entry.lexical_rank == (
                ranking.lexical_ranking.index(entry.skill_id) + 1
                if entry.skill_id in ranking.lexical_ranking
                else None
            )
            assert entry.semantic_rank == (
                ranking.semantic_ranking.index(entry.skill_id) + 1
                if entry.skill_id in ranking.semantic_ranking
                else None
            )
        shared = set(ranking.lexical_ranking) & set(ranking.semantic_ranking)
        assert index.corpus.ids_by_name['React'] in shared
        assert _entry_names(index, ranking)[0] == 'React'

    def test_should_refresh_the_ranking_with_the_full_answer_set(
        self, index: _Index
    ) -> None:
        intent = 'Quero aprender a fazer sites'
        alone = index.provider.retrieve(_query(intent))
        structure = index.provider.retrieve(
            _query(
                intent,
                (
                    'Quero começar pela estrutura e pela aparência das páginas',
                    'Ainda não sei programar',
                ),
            )
        )
        behavior = index.provider.retrieve(
            _query(intent, ('Já sei HTML e CSS', 'Quero interatividade e componentes'))
        )

        assert _entry_names(index, structure)[0] == 'HTML e CSS'
        assert structure.entries != behavior.entries
        assert _entry_names(index, behavior).index('React') < _entry_names(
            index, structure
        ).index('React')
        assert alone.lexical_ranking != behavior.lexical_ranking
        assert alone.semantic_ranking != behavior.semantic_ranking

    def test_should_rank_the_requested_skill_above_the_negated_one(
        self, index: _Index
    ) -> None:
        names = _entry_names(
            index,
            index.provider.retrieve(
                _query(
                    'Não quero front-end nem páginas, prefiro APIs e regras de '
                    'negócio no servidor'
                )
            ),
        )

        assert names[0] == 'APIs web'
        assert names.index('APIs web') < names.index('HTML e CSS')

    def test_should_compose_candidates_with_authorized_catalog_data(
        self, index: _Index
    ) -> None:
        retrieval = RetrievePlanningSkillsUseCase(
            index.provider, index.corpus.catalog
        ).execute(
            _query('Quero construir interfaces com componentes e estado usando React')
        )
        react = retrieval.candidates[0]

        assert retrieval.index_version == index.version
        assert react.name == 'React'
        assert react.description == 'Construa interfaces com componentes e estado.'
        assert set(react.foundation_skill_ids) == {
            index.corpus.ids_by_name['JavaScript essencial'],
            index.corpus.ids_by_name['HTML e CSS'],
        }
        assert react.lexical_rank == 1
        assert react.semantic_rank == 1
        assert {candidate.name for candidate in retrieval.candidates} <= set(
            index.corpus.ids_by_name
        )
        assert len({candidate.skill_id for candidate in retrieval.candidates}) == len(
            retrieval.candidates
        )


class TestPlanningIntentClassification:
    def test_should_classify_the_labeled_sets_through_the_decision_contract(
        self,
    ) -> None:
        resources = PlannerResources()
        labeled = [
            (item.text, item.label)
            for item in (
                *resources.intent_evaluation.calibration,
                *resources.intent_evaluation.held_out,
            )
        ]
        double = _JevDouble(dict(labeled))
        use_case = ClassifyPlanningIntentUseCase(_classifier(double.handler))

        matrix, accuracy, undue_refusals = _evaluate(use_case, labeled)
        _print_matrix('transport double', matrix)
        result = use_case.execute(
            PlanningQuery(intent=labeled[0][0], answers=('Nunca programei',))
        )

        assert accuracy == 1.0
        assert undue_refusals == 0
        assert len(double.requests) == len(labeled) + 1
        assert double.requests[-1]['state'] == {
            'intent': labeled[0][0],
            'answers': ['Nunca programei'],
        }
        assert [label for label, _ in result.probabilities] == [
            'ambiguous',
            'learning',
            'out-of-scope',
        ]
        assert [value for _, value in result.probabilities] == pytest.approx(
            [0.05, 0.9, 0.05]
        )

    @pytest.mark.parametrize(
        ('choice', 'confidence', 'expected'),
        [
            ('learning', 0.95, PlanningIntentKind.LEARNING),
            ('learning', 0.4, PlanningIntentKind.AMBIGUOUS),
            ('out-of-scope', 0.95, PlanningIntentKind.OUT_OF_SCOPE),
            ('out-of-scope', 0.5, PlanningIntentKind.AMBIGUOUS),
            ('ambiguous', 0.34, PlanningIntentKind.AMBIGUOUS),
        ],
    )
    def test_should_downgrade_low_confidence_decisions_to_clarification(
        self, choice: str, confidence: float, expected: PlanningIntentKind
    ) -> None:
        classification = ClassifyPlanningIntentUseCase(
            _classifier(lambda _request: _decision(choice, confidence))
        ).execute(_query('Quero evoluir'))

        assert classification.kind is expected
        assert classification.confidence == confidence

    def test_should_recover_from_one_retryable_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(jev_module, 'sleep', _no_sleep)
        statuses = iter((503, 200))

        def handler(_request: httpx.Request) -> httpx.Response:
            status = next(statuses)
            return (
                _decision('learning', 0.9)
                if status == 200
                else httpx.Response(status, json={'error': 'busy'})
            )

        classification = _classifier(handler).classify(_query('Quero aprender React'))

        assert classification.kind is PlanningIntentKind.LEARNING
        assert next(statuses, None) is None

    @pytest.mark.parametrize(
        ('name', 'respond', 'expected_requests'),
        [
            ('retryable exhausted', lambda: httpx.Response(503, json={}), 3),
            ('bad request', lambda: httpx.Response(400, json={}), 1),
            ('not json', lambda: httpx.Response(200, text='not json'), 1),
            ('missing answer', lambda: httpx.Response(200, json={'answers': {}}), 1),
            ('choice outside the set', lambda: _decision('maybe', 0.9), 1),
            (
                'probabilities outside the set',
                lambda: httpx.Response(
                    200,
                    json={
                        'answers': {
                            'planning_intent': {
                                'type': 'choice',
                                'choice': 'learning',
                                'confidence': 0.9,
                                'probabilities': {'learning': 0.9, 'other': 0.1},
                            }
                        }
                    },
                ),
                1,
            ),
            (
                'probabilities not summing to one',
                lambda: httpx.Response(
                    200,
                    json={
                        'answers': {
                            'planning_intent': {
                                'type': 'choice',
                                'choice': 'learning',
                                'confidence': 0.9,
                                'probabilities': {
                                    'learning': 0.9,
                                    'out-of-scope': 0.9,
                                    'ambiguous': 0.9,
                                },
                            }
                        }
                    },
                ),
                1,
            ),
        ],
    )
    def test_should_raise_the_typed_error_instead_of_a_refusal_on_technical_failures(
        self,
        monkeypatch: pytest.MonkeyPatch,
        name: str,
        respond: Callable[[], httpx.Response],
        expected_requests: int,
    ) -> None:
        del name
        monkeypatch.setattr(jev_module, 'sleep', _no_sleep)
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return respond()

        with pytest.raises(PlanningClassificationUnavailableError):
            ClassifyPlanningIntentUseCase(_classifier(handler)).execute(
                _query('Quero aprender React')
            )
        assert len(requests) == expected_requests

    def test_should_retry_transport_errors_before_failing_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(jev_module, 'sleep', _no_sleep)
        attempts: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(request)
            raise httpx.ConnectError('down', request=request)

        with pytest.raises(PlanningClassificationUnavailableError):
            _classifier(handler).classify(_query('Quero aprender React'))
        assert len(attempts) == 3

    def test_should_fail_closed_without_an_api_key(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _decision('learning', 0.9)

        with pytest.raises(PlanningClassificationUnavailableError):
            _classifier(handler, api_key=None).classify(_query('Quero aprender'))
        assert requests == []

    def test_should_reject_thresholds_outside_the_closed_set(self) -> None:
        with pytest.raises(ValueError, match='thresholds'):
            JevPlanningIntentClassifierProvider(
                httpx.Client(), 'test-key', _DECISIONS_URL, _MODEL, {'learning': 0.5}
            )


class _ShortEmbeddings:
    """Embeddings double with the wrong dimension for the preparation guard."""

    def embed_queries(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.0, 0.0, 1.0) for _ in texts)

    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.0, 0.0, 1.0) for _ in texts)


class TestPlanningPreparationGuards:
    def test_should_reject_an_empty_catalog_and_incompatible_vectors(
        self,
        postgres_database: PostgresDatabase,
        embeddings: SentenceTransformersEmbeddingsProvider,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
    ) -> None:
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        catalog = DatabaseCurriculumCatalogProvider(curriculum)
        repository = PlanningEmbeddingsDatabaseRepository(
            SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        )

        with pytest.raises(ValueError, match='at least one authorized Skill'):
            prepare_indexes(
                embeddings, repository, catalog, PlannerResources(), preprocessor
            )
        with curriculum.transaction() as repositories:
            repositories.skills.add_many(list(build_development_seed().skills))
        with pytest.raises(ValueError, match='embedding dimension'):
            prepare_indexes(
                _ShortEmbeddings(),
                repository,
                catalog,
                PlannerResources(),
                preprocessor,
            )
        assert repository.find_active_version() is None

    def test_should_fail_closed_when_the_index_cannot_serve_the_current_catalog(
        self, postgres_database: PostgresDatabase
    ) -> None:
        catalog = DatabaseCurriculumCatalogProvider(
            SqlalchemyCurriculumDatabase(postgres_database.engine)
        )
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        repository = PlanningEmbeddingsDatabaseRepository(database)
        resources = PlannerResources()
        resources.bind_catalog(())
        # The active version matches an empty catalog, which no provider can serve.
        repository.prepare_version(
            resources.version,
            (PlanningIndexedEmbedding(skill_id='ghost', vector=_axis(0)),),
        )
        repository.activate_version(resources.version)

        with pytest.raises(PlanningIndexUnavailableError):
            LazyPlanningSkillRetrievalProvider(database, catalog).retrieve(
                _query('Quero aprender React')
            )

    def test_should_require_a_unique_non_empty_catalog_for_the_lexical_index(
        self,
        corpus: _Corpus,
        embeddings: SentenceTransformersEmbeddingsProvider,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
    ) -> None:
        skill = corpus.catalog.list_skills()[0]
        for skills in ((), (skill, skill)):
            with pytest.raises(ValueError, match='non-empty unique catalog'):
                TfidfSentenceTransformersPlanningSkillRetrievalProvider(
                    skills,
                    embeddings,
                    corpus.repository,
                    preprocessor,
                    PlannerResources(),
                )

    def test_should_fall_back_to_the_semantic_ranking_for_a_stop_word_query(
        self, index: _Index
    ) -> None:
        ranking = index.provider.retrieve(_query('Eu quero isso e aquilo'))

        assert ranking.lexical_ranking == ()
        assert ranking.semantic_ranking
        assert all(entry.lexical_rank is None for entry in ranking.entries)


def _set_dimension(data: dict[str, Any]) -> None:
    data['dimension'] = 512


def _break_threshold(data: dict[str, Any]) -> None:
    data['intent_thresholds']['learning'] = 1.5


def _empty_held_out(data: dict[str, Any]) -> None:
    data['held_out'] = []


def _empty_queries(data: dict[str, Any]) -> None:
    data['queries'] = []


class TestPlannerResources:
    @pytest.mark.parametrize(
        ('name', 'mutate', 'message'),
        [
            (
                'planner-index-manifest.json',
                _set_dimension,
                'Invalid Planner index manifest',
            ),
            (
                'planner-index-manifest.json',
                _break_threshold,
                'Invalid Planner index manifest',
            ),
            (
                'planner-intent-evaluation.json',
                _empty_held_out,
                'cannot be empty',
            ),
            (
                'planner-retrieval-evaluation.json',
                _empty_queries,
                'cannot be empty',
            ),
        ],
    )
    def test_should_reject_inconsistent_resources(
        self,
        monkeypatch: pytest.MonkeyPatch,
        name: str,
        mutate: Callable[[dict[str, Any]], object],
        message: str,
    ) -> None:
        original = planner_resources_module._read_resource  # noqa: SLF001 # pyright: ignore[reportPrivateUsage] - test seam of the resource loader.

        def patched(resource: str) -> str:
            text = original(resource)
            if resource != name:
                return text
            data = cast('dict[str, Any]', json.loads(text))
            mutate(data)
            return json.dumps(data, ensure_ascii=False)

        monkeypatch.setattr(planner_resources_module, '_read_resource', patched)

        with pytest.raises(ValueError, match=message):
            PlannerResources()

    def test_should_bind_the_catalog_into_the_version(self) -> None:
        unbound = PlannerResources()
        bound = PlannerResources()
        bound.bind_catalog(())
        again = PlannerResources()
        again.bind_catalog(())

        assert unbound.version != bound.version
        assert bound.version == again.version

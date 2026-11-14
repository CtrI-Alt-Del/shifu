from __future__ import annotations
import json
import os
import subprocess
import sys
from math import sqrt
from pathlib import Path
from typing import Any, cast, TYPE_CHECKING
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as SqlalchemySession
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.intelligence.ai.data import planner_resources as planner_resources_module
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.errors import (
    PlanningIndexUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningIndexedEmbedding,
)
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PLANNING_EMBEDDING_DIMENSION,
)
from shifu.intelligence.core.use_cases import (
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
from tests.fixtures.curriculum_planning_boundary_fixture import (
    BoundaryCorpus,
    BoundaryIndex,
    BoundaryShortEmbeddings,
    boundary_query,
    boundary_set_dimension,
    boundary_break_threshold,
    boundary_empty_held_out,
    boundary_empty_queries,
    retrieve_index,
)
from tests.fixtures.curriculum_planning_boundary_fixture import (
    corpus as corpus,
    index as index,
    embeddings as embeddings,
    preprocessor as preprocessor,
)
from tests.fixtures.curriculum_planning_boundary_fixture import prepare_corpus
from shifu.shared.core.domain.errors import ServiceUnavailableError


if TYPE_CHECKING:
    from collections.abc import Callable
    from tests.fixtures.postgres_fixture import PostgresDatabase
    from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
        SentenceTransformersEmbeddingsProvider,
    )


class TestPlanningPreparationConfiguration:
    def test_should_require_negation_tokens_from_the_manifest(self) -> None:
        """Defensive constructor configuration only; no preparation executes."""
        with pytest.raises(ValueError, match='negation'):
            SpacyPlanningTextPreprocessorProvider(())


class TestPlanningIndexPreparation:
    def test_should_fail_closed_without_an_active_index(
        self,
        corpus: BoundaryCorpus,
        embeddings: SentenceTransformersEmbeddingsProvider,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
    ) -> None:
        resources = PlannerResources()
        skills = corpus.catalog.list_skills()
        resources.bind_catalog(skills)
        provider = TfidfSentenceTransformersPlanningSkillRetrievalProvider(
            skills, embeddings, corpus.repository, preprocessor, resources
        )
        query = boundary_query('Quero aprender React')

        with pytest.raises(PlanningIndexUnavailableError):
            RetrievePlanningSkillsUseCase(provider, corpus.catalog).execute(query)
        with pytest.raises(PlanningIndexUnavailableError):
            RetrievePlanningSkillsUseCase(
                LazyPlanningSkillRetrievalProvider(
                    corpus.database, corpus.catalog, semantic_model='e5'
                ),
                corpus.catalog,
            ).execute(query)
        with pytest.raises(PlanningIndexUnavailableError):
            RetrievePlanningSkillsUseCase(provider, corpus.catalog).execute(query)
        assert corpus.repository.find_active_version() is None

    def test_should_prepare_one_normalized_vector_per_skill_under_one_active_version(
        self,
        index: BoundaryIndex,
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
                (PlanningIndexedEmbedding(skill_id='skill', vector=boundary_axis(0)),),
            )

        # Promoting another version deactivates the current one atomically.
        index.corpus.repository.prepare_version(
            'older',
            (PlanningIndexedEmbedding(skill_id='skill', vector=boundary_axis(0)),),
        )
        index.corpus.repository.activate_version('older')
        assert index.corpus.repository.find_active_version() == 'older'
        with pytest.raises(PlanningIndexUnavailableError):
            retrieve_index(index, boundary_query('Quero aprender React'))

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
        self, corpus: BoundaryCorpus, postgres_database: PostgresDatabase
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

        lazy = LazyPlanningSkillRetrievalProvider(
            corpus.database, corpus.catalog, semantic_model='e5'
        )
        use_case = RetrievePlanningSkillsUseCase(lazy, corpus.catalog)
        ranking = use_case.execute(boundary_query('Quero aprender React'))

        assert ranking.index_version == resources.version
        assert ranking.candidates[0].name == 'React'
        assert (
            use_case.execute(boundary_query('Quero aprender React')).candidates
            == ranking.candidates
        )


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
                BoundaryShortEmbeddings(),
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
            (PlanningIndexedEmbedding(skill_id='ghost', vector=boundary_axis(0)),),
        )
        repository.activate_version(resources.version)

        with pytest.raises(PlanningIndexUnavailableError):
            RetrievePlanningSkillsUseCase(
                LazyPlanningSkillRetrievalProvider(
                    database, catalog, semantic_model='e5'
                ),
                catalog,
            ).execute(boundary_query('Quero aprender React'))

    def test_should_require_a_unique_non_empty_catalog_for_the_lexical_index(
        self,
        corpus: BoundaryCorpus,
        embeddings: SentenceTransformersEmbeddingsProvider,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
    ) -> None:
        """Defensive constructor configuration only; no retrieval executes."""
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


class TestPlannerResources:
    @pytest.mark.parametrize(
        ('name', 'mutate', 'message'),
        [
            (
                'planner-index-manifest.json',
                boundary_set_dimension,
                'Invalid Planner index manifest',
            ),
            (
                'planner-index-manifest.json',
                boundary_break_threshold,
                'Invalid Planner index manifest',
            ),
            (
                'planner-intent-evaluation.json',
                boundary_empty_held_out,
                'cannot be empty',
            ),
            (
                'planner-retrieval-evaluation.json',
                boundary_empty_queries,
                'cannot be empty',
            ),
        ],
    )
    def test_should_reject_inconsistent_resources(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        name: str,
        mutate: Callable[[dict[str, Any]], object],
        message: str,
    ) -> None:
        original = planner_resources_module.files

        resource_root = tmp_path / 'planner-resources'
        resource_root.mkdir()
        for resource in original('shifu.intelligence.ai.data').iterdir():
            if not resource.name.endswith('.json'):
                continue
            text = resource.read_text(encoding='utf-8')
            if resource.name == name:
                data = cast('dict[str, Any]', json.loads(text))
                mutate(data)
                text = json.dumps(data, ensure_ascii=False)
            (resource_root / resource.name).write_text(text, encoding='utf-8')

        def resources_path(_package: str) -> Path:
            return resource_root

        monkeypatch.setattr(planner_resources_module, 'files', resources_path)

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


def boundary_axis(index: int) -> tuple[float, ...]:
    vector = [0.0] * PLANNING_EMBEDDING_DIMENSION
    vector[index] = 1.0
    return tuple(vector)


def _blend(first: int, second: int, weight: float) -> tuple[float, ...]:
    vector = [0.0] * PLANNING_EMBEDDING_DIMENSION
    vector[first] = weight
    vector[second] = sqrt(1 - weight * weight)
    return tuple(vector)


def _corpus(*skill_ids: str) -> tuple[PlanningIndexedEmbedding, ...]:
    return tuple(
        PlanningIndexedEmbedding(skill_id=skill_id, vector=boundary_axis(index))
        for index, skill_id in enumerate(skill_ids)
    )


class TestPreparedPlanningIndexLifecycle:
    @pytest.fixture(autouse=True)
    def setup(self, postgres_database: PostgresDatabase) -> None:
        self.repository = PlanningEmbeddingsDatabaseRepository(
            SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        )

    def test_should_search_only_the_active_version_among_eligible_skills(
        self,
    ) -> None:
        assert self.repository.find_active_version() is None
        # An inactive persisted version is a precondition, not the preparation action.
        self.repository.prepare_version('v1', _corpus('skill-a', 'skill-b', 'skill-c'))
        with pytest.raises(ServiceUnavailableError):
            self.repository.find_nearest('v1', boundary_axis(0), ('skill-a',), 10)

        prepare_corpus(self.repository, 'v1', _corpus('skill-a', 'skill-b', 'skill-c'))
        query = _blend(0, 1, 0.8)
        matches = self.repository.find_nearest(
            'v1', query, ('skill-a', 'skill-b', 'skill-c'), 10
        )

        assert self.repository.find_active_version() == 'v1'
        assert [match.skill_id for match in matches] == [
            'skill-a',
            'skill-b',
            'skill-c',
        ]
        assert [round(match.similarity, 3) for match in matches] == [0.8, 0.6, 0.0]
        assert [
            match.skill_id
            for match in self.repository.find_nearest('v1', query, ('skill-b',), 10)
        ] == ['skill-b']
        assert (
            len(
                self.repository.find_nearest(
                    'v1', query, ('skill-a', 'skill-b', 'skill-c'), 2
                )
            )
            == 2
        )
        assert self.repository.find_nearest('v1', query, (), 10) == ()
        assert self.repository.find_nearest('v1', query, ('skill-a',), 0) == ()

    def test_should_replace_the_active_version_and_keep_it_immutable(self) -> None:
        prepare_corpus(self.repository, 'v1', _corpus('skill-a', 'skill-b'))
        self.repository.activate_version('v1')
        prepare_corpus(self.repository, 'v2', _corpus('skill-b', 'skill-a'))
        self.repository.activate_version('v2')

        assert self.repository.find_active_version() == 'v2'
        with pytest.raises(ValueError, match='Active immutable index'):
            prepare_corpus(self.repository, 'v2', _corpus('skill-a'))
        with pytest.raises(ServiceUnavailableError):
            self.repository.find_nearest('v1', boundary_axis(0), ('skill-a',), 10)

        # An inactive version can be rebuilt and promoted again.
        prepare_corpus(self.repository, 'v1', _corpus('skill-c'))
        self.repository.activate_version('v1')
        matches = self.repository.find_nearest(
            'v1', boundary_axis(0), ('skill-a', 'skill-b', 'skill-c'), 10
        )

        assert self.repository.find_active_version() == 'v1'
        assert [match.skill_id for match in matches] == ['skill-c']

    def test_should_reject_invalid_corpora_versions_and_queries(self) -> None:
        with pytest.raises(
            ValueError, match=r'complete corpus|at least one authorized Skill'
        ):
            prepare_corpus(self.repository, '', _corpus('skill-a'))
        with pytest.raises(
            ValueError, match=r'complete corpus|at least one authorized Skill'
        ):
            prepare_corpus(self.repository, 'v1', ())
        with pytest.raises(ValueError, match='Duplicate Skill'):
            prepare_corpus(
                self.repository, 'v1', (*_corpus('skill-a'), *_corpus('skill-a'))
            )
        with pytest.raises(ServiceUnavailableError):
            self.repository.activate_version('missing')

        prepare_corpus(self.repository, 'v1', _corpus('skill-a'))
        self.repository.activate_version('v1')

        with pytest.raises(ValueError, match='dimensions'):
            self.repository.find_nearest('v1', (1.0, 0.0), ('skill-a',), 10)
        with pytest.raises(ValueError, match='normalized'):
            self.repository.find_nearest(
                'v1',
                tuple(0.5 for _ in range(PLANNING_EMBEDDING_DIMENSION)),
                ('skill-a',),
                10,
            )
        assert self.repository.find_active_version() == 'v1'

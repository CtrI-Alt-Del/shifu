from math import sqrt

import pytest

from shifu.intelligence.core.domain.structures import PlanningIndexedEmbedding
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PLANNING_EMBEDDING_DIMENSION,
)
from shifu.intelligence.database.planning_embeddings_database_repository import (
    PlanningEmbeddingsDatabaseRepository,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.fixtures.postgres_fixture import PostgresDatabase


def _axis(index: int) -> tuple[float, ...]:
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
        PlanningIndexedEmbedding(skill_id=skill_id, vector=_axis(index))
        for index, skill_id in enumerate(skill_ids)
    )


class TestSqlalchemyPlanningEmbeddingsRepository:
    @pytest.fixture(autouse=True)
    def setup(self, postgres_database: PostgresDatabase) -> None:
        self.repository = PlanningEmbeddingsDatabaseRepository(
            SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        )

    def test_should_search_only_the_active_version_among_eligible_skills(
        self,
    ) -> None:
        assert self.repository.find_active_version() is None
        self.repository.prepare_version('v1', _corpus('skill-a', 'skill-b', 'skill-c'))
        with pytest.raises(ServiceUnavailableError):
            self.repository.find_nearest('v1', _axis(0), ('skill-a',), 10)

        self.repository.activate_version('v1')
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
        self.repository.prepare_version('v1', _corpus('skill-a', 'skill-b'))
        self.repository.activate_version('v1')
        self.repository.prepare_version('v2', _corpus('skill-b', 'skill-a'))
        self.repository.activate_version('v2')

        assert self.repository.find_active_version() == 'v2'
        with pytest.raises(ValueError, match='Active immutable index'):
            self.repository.prepare_version('v2', _corpus('skill-a'))
        with pytest.raises(ServiceUnavailableError):
            self.repository.find_nearest('v1', _axis(0), ('skill-a',), 10)

        # An inactive version can be rebuilt and promoted again.
        self.repository.prepare_version('v1', _corpus('skill-c'))
        self.repository.activate_version('v1')
        matches = self.repository.find_nearest(
            'v1', _axis(0), ('skill-a', 'skill-b', 'skill-c'), 10
        )

        assert self.repository.find_active_version() == 'v1'
        assert [match.skill_id for match in matches] == ['skill-c']

    def test_should_reject_invalid_corpora_versions_and_queries(self) -> None:
        with pytest.raises(ValueError, match='complete corpus'):
            self.repository.prepare_version('', _corpus('skill-a'))
        with pytest.raises(ValueError, match='complete corpus'):
            self.repository.prepare_version('v1', ())
        with pytest.raises(ValueError, match='Duplicate Skill'):
            self.repository.prepare_version(
                'v1', (*_corpus('skill-a'), *_corpus('skill-a'))
            )
        with pytest.raises(ServiceUnavailableError):
            self.repository.activate_version('missing')

        self.repository.prepare_version('v1', _corpus('skill-a'))
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

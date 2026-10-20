from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.errors import PlanningIndexUnavailableError
from shifu.intelligence.core.domain.structures import (
    PlanningQuery,
    PlanningSkillCandidate,
    PlanningSkillRankEntry,
    PlanningSkillRanking,
)
from shifu.intelligence.core.interfaces import PlanningSkillRetrievalProvider
from shifu.intelligence.core.use_cases import RetrievePlanningSkillsUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    SkillCatalogEntry,
    SkillFoundationEntry,
)
from shifu.shared.core.interfaces import CurriculumCatalogProvider

_RRF_K = 60


def _rrf(*ranks: int) -> float:
    return sum(1 / (_RRF_K + rank) for rank in ranks)


class TestRetrievePlanningSkillsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.retrieval = create_autospec(PlanningSkillRetrievalProvider, instance=True)
        self.catalog = create_autospec(CurriculumCatalogProvider, instance=True)
        self.catalog.list_skills.return_value = (
            SkillCatalogEntry(
                id='skill-apis',
                name='APIs web',
                description='Conecte dados e regras por interfaces HTTP.',
            ),
            SkillCatalogEntry(
                id='skill-html',
                name='HTML e CSS',
                description='Estruture páginas e defina sua apresentação visual.',
            ),
            SkillCatalogEntry(
                id='skill-logic',
                name='Lógica de programação',
                description='Fundamentos para programar.',
            ),
        )
        self.catalog.find_direct_foundations_for_many.return_value = {
            'skill-apis': [
                SkillFoundationEntry(skill_id='skill-logic', name='Lógica'),
                SkillFoundationEntry(skill_id='skill-logic', name='Lógica'),
            ],
        }
        self.use_case = RetrievePlanningSkillsUseCase(self.retrieval, self.catalog)
        self.query = PlanningQuery(
            intent='Não quero front-end, prefiro APIs', answers=('Já sei HTML',)
        )
        self.ranking = PlanningSkillRanking(
            index_version='index-v1',
            lexical_ranking=('skill-apis', 'skill-html'),
            semantic_ranking=('skill-apis', 'skill-unknown'),
            entries=(
                PlanningSkillRankEntry(
                    skill_id='skill-apis',
                    score=_rrf(1, 1),
                    lexical_rank=1,
                    semantic_rank=1,
                ),
                PlanningSkillRankEntry(
                    skill_id='skill-html',
                    score=_rrf(2),
                    lexical_rank=2,
                    semantic_rank=None,
                ),
                PlanningSkillRankEntry(
                    skill_id='skill-unknown',
                    score=_rrf(2) - 1e-9,
                    lexical_rank=None,
                    semantic_rank=2,
                ),
            ),
        )
        self.retrieval.retrieve.return_value = self.ranking

    def test_should_describe_existing_candidates_with_catalog_text_and_foundations(
        self,
    ) -> None:
        result = self.use_case.execute(self.query)

        assert result.index_version == 'index-v1'
        assert result.lexical_ranking == ('skill-apis', 'skill-html')
        assert result.semantic_ranking == ('skill-apis', 'skill-unknown')
        assert result.candidates == (
            PlanningSkillCandidate(
                skill_id='skill-apis',
                name='APIs web',
                description='Conecte dados e regras por interfaces HTTP.',
                foundation_skill_ids=('skill-logic',),
                score=_rrf(1, 1),
                lexical_rank=1,
                semantic_rank=1,
            ),
            PlanningSkillCandidate(
                skill_id='skill-html',
                name='HTML e CSS',
                description='Estruture páginas e defina sua apresentação visual.',
                foundation_skill_ids=(),
                score=_rrf(2),
                lexical_rank=2,
                semantic_rank=None,
            ),
        )
        self.retrieval.retrieve.assert_called_once_with(self.query)
        self.catalog.find_direct_foundations_for_many.assert_called_once_with(
            ['skill-apis', 'skill-html', 'skill-unknown']
        )

    def test_should_drop_identifiers_absent_from_the_authorized_catalog(self) -> None:
        result = self.use_case.execute(self.query)

        assert 'skill-unknown' not in {
            candidate.skill_id for candidate in result.candidates
        }

    def test_should_return_no_candidates_when_the_rankings_are_empty(self) -> None:
        self.retrieval.retrieve.return_value = PlanningSkillRanking(
            index_version='index-v1',
            lexical_ranking=(),
            semantic_ranking=(),
            entries=(),
        )

        result = self.use_case.execute(self.query)

        assert result.candidates == ()
        assert result.index_version == 'index-v1'

    def test_should_propagate_the_typed_index_error_without_reading_the_catalog(
        self,
    ) -> None:
        error = PlanningIndexUnavailableError()
        self.retrieval.retrieve.side_effect = error

        with pytest.raises(PlanningIndexUnavailableError) as raised:
            self.use_case.execute(self.query)

        assert raised.value is error
        self.catalog.list_skills.assert_not_called()
        self.catalog.find_direct_foundations_for_many.assert_not_called()

    @pytest.mark.parametrize(
        'error', [ServiceUnavailableError(), ValueError('Invalid vector')]
    )
    def test_should_map_a_technical_failure_to_the_typed_index_error(
        self, error: Exception
    ) -> None:
        self.retrieval.retrieve.side_effect = error

        with pytest.raises(PlanningIndexUnavailableError) as raised:
            self.use_case.execute(self.query)

        assert raised.value.__cause__ is error
        assert raised.value.message == (
            'O índice de Habilidades do Planejador está indisponível.'
        )
        self.catalog.list_skills.assert_not_called()

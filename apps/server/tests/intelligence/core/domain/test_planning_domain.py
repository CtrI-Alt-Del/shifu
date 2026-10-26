from collections.abc import Callable
from math import nan, sqrt

import pytest

from shifu.intelligence.core.domain.enums import PlanningIntentKind
from shifu.intelligence.core.domain.structures import (
    PlanningEmbeddingMatch,
    PlanningIndexedEmbedding,
    PlanningIntentClassification,
    PlanningQuery,
    PlanningSkillCandidate,
    PlanningSkillRankEntry,
    PlanningSkillRanking,
    PlanningSkillRetrieval,
)
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PLANNING_EMBEDDING_DIMENSION,
)
from shifu.intelligence.core.domain.structures.planning_skill_ranking import (
    CANDIDATE_LIMIT,
    LEXICAL_LIMIT,
    SEMANTIC_LIMIT,
)

_PROBABILITIES = (('ambiguous', 0.05), ('learning', 0.9), ('out-of-scope', 0.05))


def _unit(index: int) -> tuple[float, ...]:
    vector = [0.0] * PLANNING_EMBEDDING_DIMENSION
    vector[index] = 1.0
    return tuple(vector)


def _entry(
    skill_id: str,
    score: float,
    lexical_rank: int | None = 1,
    semantic_rank: int | None = None,
) -> PlanningSkillRankEntry:
    return PlanningSkillRankEntry(
        skill_id=skill_id,
        score=score,
        lexical_rank=lexical_rank,
        semantic_rank=semantic_rank,
    )


def _candidate(
    skill_id: str,
    score: float,
    foundation_skill_ids: tuple[str, ...] = (),
    **changes: object,
) -> PlanningSkillCandidate:
    values: dict[str, object] = {
        'skill_id': skill_id,
        'name': f'Skill {skill_id}',
        'description': 'Descrição.',
        'foundation_skill_ids': foundation_skill_ids,
        'score': score,
        'lexical_rank': 1,
        'semantic_rank': None,
    }
    values.update(changes)
    return PlanningSkillCandidate(**values)  # pyright: ignore[reportArgumentType] - scenario overrides are typed per field.


def _ranking(
    lexical: tuple[str, ...],
    semantic: tuple[str, ...],
    *entries: PlanningSkillRankEntry,
) -> PlanningSkillRanking:
    return PlanningSkillRanking(
        index_version='v1',
        lexical_ranking=lexical,
        semantic_ranking=semantic,
        entries=entries,
    )


def test_should_build_valid_planning_values() -> None:
    query = PlanningQuery(intent='Quero aprender React', answers=('Já sei HTML',))
    classification = PlanningIntentClassification(
        kind=PlanningIntentKind.LEARNING, confidence=0.9, probabilities=_PROBABILITIES
    )
    ranking = _ranking(
        ('a', 'b'),
        ('b', 'c'),
        _entry('b', 1 / 62 + 1 / 61, lexical_rank=2, semantic_rank=1),
        _entry('a', 1 / 61),
        _entry('c', 1 / 62, lexical_rank=None, semantic_rank=2),
    )
    retrieval = PlanningSkillRetrieval(
        index_version='v1',
        lexical_ranking=('a',),
        semantic_ranking=(),
        candidates=(_candidate('a', 0.5, ('z',)), _candidate('b', 0.4)),
    )
    embedding = PlanningIndexedEmbedding(skill_id='a', vector=_unit(3))
    match = PlanningEmbeddingMatch(skill_id='a', similarity=0.73)

    assert query.answers == ('Já sei HTML',)
    assert classification.kind is PlanningIntentKind.LEARNING
    assert [entry.skill_id for entry in ranking.entries] == ['b', 'a', 'c']
    assert retrieval.candidates[0].foundation_skill_ids == ('z',)
    assert sqrt(sum(value * value for value in embedding.vector)) == 1.0
    assert match.similarity == 0.73


@pytest.mark.parametrize(
    'build',
    [
        lambda: PlanningQuery(intent='   '),
        lambda: PlanningQuery(intent='Quero aprender', answers=('ok', ' ')),
        lambda: PlanningIntentClassification(
            kind=PlanningIntentKind.LEARNING,
            confidence=1.5,
            probabilities=_PROBABILITIES,
        ),
        lambda: PlanningIntentClassification(
            kind=PlanningIntentKind.LEARNING,
            confidence=nan,
            probabilities=_PROBABILITIES,
        ),
        lambda: PlanningIntentClassification(
            kind=PlanningIntentKind.LEARNING,
            confidence=0.9,
            probabilities=(('learning', 0.9), ('ambiguous', 0.1)),
        ),
        lambda: PlanningIntentClassification(
            kind=PlanningIntentKind.LEARNING,
            confidence=0.9,
            probabilities=(
                ('ambiguous', -0.2),
                ('learning', 1.2),
                ('out-of-scope', 0.0),
            ),
        ),
        lambda: PlanningIntentClassification(
            kind=PlanningIntentKind.LEARNING,
            confidence=0.9,
            probabilities=(
                ('ambiguous', 0.1),
                ('learning', 0.1),
                ('out-of-scope', 0.1),
            ),
        ),
        lambda: _entry('', 0.1),
        lambda: _entry('a', 0.0),
        lambda: _entry('a', nan),
        lambda: _entry('a', 0.1, lexical_rank=None, semantic_rank=None),
        lambda: _entry('a', 0.1, lexical_rank=0),
        lambda: PlanningSkillRanking(
            index_version='', lexical_ranking=(), semantic_ranking=(), entries=()
        ),
        lambda: _ranking(tuple(str(index) for index in range(LEXICAL_LIMIT + 1)), ()),
        lambda: _ranking((), tuple(str(index) for index in range(SEMANTIC_LIMIT + 1))),
        lambda: _ranking(('a', 'a'), ()),
        lambda: _ranking(
            tuple(str(index) for index in range(LEXICAL_LIMIT)),
            tuple(str(index) for index in range(LEXICAL_LIMIT, 2 * SEMANTIC_LIMIT)),
            *(
                _entry(str(index), 1 / (CANDIDATE_LIMIT + 2 + index))
                for index in range(CANDIDATE_LIMIT + 1)
            ),
        ),
        lambda: _ranking(('a',), (), _entry('a', 0.2), _entry('a', 0.1)),
        lambda: _ranking(('a',), (), _entry('b', 0.2)),
        lambda: _ranking(('a', 'b'), (), _entry('a', 0.1), _entry('b', 0.2)),
        lambda: _ranking(('a', 'b'), (), _entry('b', 0.1), _entry('a', 0.1)),
        lambda: _candidate('a', 0.1, name=''),
        lambda: _candidate('', 0.1),
        lambda: _candidate('a', 0.0),
        lambda: _candidate('a', 0.1, lexical_rank=None, semantic_rank=None),
        lambda: _candidate('a', 0.1, ('b', 'b')),
        lambda: _candidate('a', 0.1, ('a',)),
        lambda: PlanningSkillRetrieval(
            index_version='', lexical_ranking=(), semantic_ranking=(), candidates=()
        ),
        lambda: PlanningSkillRetrieval(
            index_version='v1',
            lexical_ranking=(),
            semantic_ranking=(),
            candidates=tuple(
                _candidate(str(index), 1 / (index + 1))
                for index in range(CANDIDATE_LIMIT + 1)
            ),
        ),
        lambda: PlanningSkillRetrieval(
            index_version='v1',
            lexical_ranking=(),
            semantic_ranking=(),
            candidates=(_candidate('a', 0.2), _candidate('a', 0.1)),
        ),
        lambda: PlanningSkillRetrieval(
            index_version='v1',
            lexical_ranking=(),
            semantic_ranking=(),
            candidates=(_candidate('a', 0.1), _candidate('b', 0.2)),
        ),
        lambda: PlanningIndexedEmbedding(skill_id='', vector=_unit(0)),
        lambda: PlanningIndexedEmbedding(skill_id='a', vector=(1.0, 0.0)),
        lambda: PlanningIndexedEmbedding(
            skill_id='a', vector=tuple(0.5 for _ in range(PLANNING_EMBEDDING_DIMENSION))
        ),
        lambda: PlanningIndexedEmbedding(
            skill_id='a',
            vector=(nan, *(0.0 for _ in range(PLANNING_EMBEDDING_DIMENSION - 1))),
        ),
        lambda: PlanningEmbeddingMatch(skill_id='', similarity=0.5),
        lambda: PlanningEmbeddingMatch(skill_id='a', similarity=nan),
    ],
)
def test_should_reject_invalid_planning_values(build: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match=r'.'):
        build()

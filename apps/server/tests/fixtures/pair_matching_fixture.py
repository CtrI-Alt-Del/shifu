from decimal import Decimal

from shifu.shared.core.domain.structures import (
    CurriculumPairMatchingConceptCriterionSnapshot,
    CurriculumPairMatchingItemSnapshot,
    CurriculumPairMatchingPairSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
)

_WORDS = ('dog', 'house', 'water', 'book', 'tree', 'sun', 'moon', 'star')
_TRANSLATIONS = (
    'cachorro',
    'casa',
    'agua',
    'livro',
    'arvore',
    'sol',
    'lua',
    'estrela',
)


def pair_matching_question(
    key: str = 'qp',
    *,
    size: int = 3,
    concept_ids: tuple[str, ...] = (),
    full_score: int | None = 100,
    partial_score: int | None = 60,
    incorrect_score: int | None = 0,
) -> CurriculumPairMatchingQuestionSnapshot:
    """Pair ``i`` joins ``word-i`` with ``translation-i``.

    The translation list is displayed rotated by one position, so the display
    order never mirrors the answer key.
    """
    translations = tuple(
        CurriculumPairMatchingItemSnapshot(
            key=f'translation-{(index + 1) % size}',
            text=_TRANSLATIONS[(index + 1) % size],
        )
        for index in range(size)
    )
    return CurriculumPairMatchingQuestionSnapshot(
        key=key,
        prompt='Associe cada palavra a sua traducao',
        source_language='en',
        target_language='pt-BR',
        words=tuple(
            CurriculumPairMatchingItemSnapshot(key=f'word-{index}', text=_WORDS[index])
            for index in range(size)
        ),
        translations=translations,
        correct_pairs=tuple(
            CurriculumPairMatchingPairSnapshot(
                word_key=f'word-{index}', translation_key=f'translation-{index}'
            )
            for index in range(size)
        ),
        full_explanation='Todos os pares estao corretos.',
        partial_explanation='Alguns pares estao corretos.',
        incorrect_explanation='Nenhum par esta correto.',
        concept_criteria=tuple(
            CurriculumPairMatchingConceptCriterionSnapshot(
                concept_id=concept_id,
                criterion='Associa vocabulario a traducao',
                examples='dog e cachorro',
                limits='Nao avalia gramatica',
                full_score=None if full_score is None else Decimal(full_score),
                partial_score=None if partial_score is None else Decimal(partial_score),
                incorrect_score=(
                    None if incorrect_score is None else Decimal(incorrect_score)
                ),
            )
            for concept_id in concept_ids
        ),
    )

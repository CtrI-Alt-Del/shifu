from shifu.curriculum.core.domain.structures import (
    PairMatchingConceptCriterion,
    PairMatchingItem,
    PairMatchingPair,
    PairMatchingQuestion,
)
from shifu.fakers.shared.pair_matching_vocabulary import (
    TRANSLATIONS,
    WORDS,
    rotated_order,
)


class PairMatchingQuestionFaker:
    """Pair ``i`` joins ``word-i`` with ``translation-i``.

    The translation list is displayed rotated by one position unless
    ``translation_order`` says otherwise, so the order never mirrors the key.
    """

    @staticmethod
    def concept_criterion(
        concept_id: str = 'concept-1',
        *,
        full_score: int | None = 100,
        partial_score: int | None = 60,
        incorrect_score: int | None = 0,
    ) -> PairMatchingConceptCriterion:
        return PairMatchingConceptCriterion(
            concept_id=concept_id,
            criterion='Associates vocabulary with its translation',
            examples='dog is cachorro',
            limits='Does not assess grammar',
            full_score=full_score,
            partial_score=partial_score,
            incorrect_score=incorrect_score,
        )

    @classmethod
    def fake(
        cls,
        *,
        key: str = 'pairs-1',
        size: int = 3,
        translation_order: tuple[int, ...] | None = None,
        prompt: str = 'Associe cada palavra a sua traducao',
        source_language: str = 'en',
        target_language: str = 'pt-BR',
        words: tuple[PairMatchingItem, ...] | None = None,
        translations: tuple[PairMatchingItem, ...] | None = None,
        correct_pairs: tuple[PairMatchingPair, ...] | None = None,
        full_explanation: str = 'Todos os pares estao corretos.',
        partial_explanation: str = 'Alguns pares estao corretos.',
        incorrect_explanation: str = 'Nenhum par esta correto.',
        concept_criteria: tuple[PairMatchingConceptCriterion, ...] = (),
    ) -> PairMatchingQuestion:
        order = translation_order or rotated_order(size)
        keyed_translations = tuple(
            PairMatchingItem(key=f'translation-{index}', text=TRANSLATIONS[index])
            for index in range(size)
        )
        return PairMatchingQuestion(
            key=key,
            prompt=prompt,
            source_language=source_language,
            target_language=target_language,
            words=words
            if words is not None
            else tuple(
                PairMatchingItem(key=f'word-{index}', text=WORDS[index])
                for index in range(size)
            ),
            translations=translations
            if translations is not None
            else tuple(keyed_translations[index] for index in order),
            correct_pairs=correct_pairs
            if correct_pairs is not None
            else tuple(
                PairMatchingPair(
                    word_key=f'word-{index}', translation_key=f'translation-{index}'
                )
                for index in range(size)
            ),
            full_explanation=full_explanation,
            partial_explanation=partial_explanation,
            incorrect_explanation=incorrect_explanation,
            concept_criteria=concept_criteria,
        )

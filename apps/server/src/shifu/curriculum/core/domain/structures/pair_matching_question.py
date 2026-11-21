from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .pair_matching_concept_criterion import PairMatchingConceptCriterion
from .pair_matching_item import PairMatchingItem
from .pair_matching_pair import PairMatchingPair

MIN_PAIRS = 2
MAX_PAIRS = 8


@structure
class PairMatchingQuestion:
    key: str
    prompt: str
    source_language: str
    target_language: str
    words: tuple[PairMatchingItem, ...]
    translations: tuple[PairMatchingItem, ...]
    correct_pairs: tuple[PairMatchingPair, ...]
    full_explanation: str
    partial_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[PairMatchingConceptCriterion, ...] = ()
    kind: Literal['pair_matching'] = 'pair_matching'

    def __post_init__(self) -> None:
        for value in (
            self.key,
            self.prompt,
            self.source_language,
            self.target_language,
            self.full_explanation,
            self.partial_explanation,
            self.incorrect_explanation,
        ):
            NonEmptyText.create(value, error_type=InvalidActivityError)

        if (
            self.kind != 'pair_matching'
            or not MIN_PAIRS <= len(self.words) <= MAX_PAIRS
            or len(self.words) != len(self.translations)
            or len(self.correct_pairs) != len(self.words)
            or len(self.concept_criteria)
            != len({item.concept_id for item in self.concept_criteria})
        ):
            raise InvalidActivityError

        self._validate_items(self.words)
        self._validate_items(self.translations)
        self._validate_answer_key()

    @staticmethod
    def _validate_items(items: tuple[PairMatchingItem, ...]) -> None:
        if len({item.key for item in items}) != len(items) or len(
            {item.text for item in items}
        ) != len(items):
            raise InvalidActivityError

    def _validate_answer_key(self) -> None:
        word_keys = [item.key for item in self.words]
        translation_keys = [item.key for item in self.translations]
        pair_words = [pair.word_key for pair in self.correct_pairs]
        pair_translations = [pair.translation_key for pair in self.correct_pairs]
        if set(pair_words) != set(word_keys) or len(set(pair_words)) != len(word_keys):
            raise InvalidActivityError

        if set(pair_translations) != set(translation_keys) or len(
            set(pair_translations)
        ) != len(translation_keys):
            raise InvalidActivityError

        expected = {pair.word_key: pair.translation_key for pair in self.correct_pairs}
        if all(
            expected[word_key] == translation_key
            for word_key, translation_key in zip(
                word_keys, translation_keys, strict=True
            )
        ):
            raise InvalidActivityError

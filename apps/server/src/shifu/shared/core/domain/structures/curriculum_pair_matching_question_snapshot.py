from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_pair_matching_concept_criterion_snapshot import (
    CurriculumPairMatchingConceptCriterionSnapshot,
)
from .curriculum_pair_matching_item_snapshot import CurriculumPairMatchingItemSnapshot
from .curriculum_pair_matching_pair_snapshot import CurriculumPairMatchingPairSnapshot


MIN_PAIRS = 2
MAX_PAIRS = 8


@structure
class CurriculumPairMatchingQuestionSnapshot:
    key: str
    prompt: str
    source_language: str
    target_language: str
    words: tuple[CurriculumPairMatchingItemSnapshot, ...]
    translations: tuple[CurriculumPairMatchingItemSnapshot, ...]
    correct_pairs: tuple[CurriculumPairMatchingPairSnapshot, ...]
    full_explanation: str
    partial_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[CurriculumPairMatchingConceptCriterionSnapshot, ...] = ()
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
            NonEmptyText.create(value, error_type=ValidationError)
        if (
            self.kind != 'pair_matching'
            or not MIN_PAIRS <= len(self.words) <= MAX_PAIRS
            or len(self.words) != len(self.translations)
            or len(self.correct_pairs) != len(self.words)
        ):
            raise ValidationError

        word_keys = [item.key for item in self.words]
        translation_keys = [item.key for item in self.translations]
        pair_words = [pair.word_key for pair in self.correct_pairs]
        pair_translations = [pair.translation_key for pair in self.correct_pairs]
        if (
            len(set(word_keys)) != len(word_keys)
            or len(set(translation_keys)) != len(translation_keys)
            or len({item.text for item in self.words}) != len(self.words)
            or len({item.text for item in self.translations}) != len(self.translations)
            or set(pair_words) != set(word_keys)
            or len(set(pair_words)) != len(pair_words)
            or set(pair_translations) != set(translation_keys)
            or len(set(pair_translations)) != len(pair_translations)
        ):
            raise ValidationError

        expected = {pair.word_key: pair.translation_key for pair in self.correct_pairs}
        if all(
            expected[word_key] == translation_key
            for word_key, translation_key in zip(
                word_keys, translation_keys, strict=True
            )
        ):
            raise ValidationError

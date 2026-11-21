from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_pair_matching_concept_criterion_snapshot import (
    CurriculumPairMatchingConceptCriterionSnapshot,
)
from .curriculum_pair_matching_item_snapshot import CurriculumPairMatchingItemSnapshot
from .curriculum_pair_matching_pair_snapshot import CurriculumPairMatchingPairSnapshot


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
            or not self.words
            or len(self.words) != len(self.translations)
            or len(self.correct_pairs) != len(self.words)
        ):
            raise ValidationError

from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.curriculum_fill_blanks_blank_snapshot import (
    CurriculumFillBlanksBlankSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_fill_blanks_concept_criterion_snapshot import (
    CurriculumFillBlanksConceptCriterionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_fill_blanks_segment_snapshot import (
    CurriculumFillBlanksSegmentSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_fill_blanks_word_snapshot import (
    CurriculumFillBlanksWordSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class CurriculumFillBlanksQuestionSnapshot:
    key: str
    prompt: str
    content_language: str
    segments: tuple[CurriculumFillBlanksSegmentSnapshot, ...]
    blanks: tuple[CurriculumFillBlanksBlankSnapshot, ...]
    bank: tuple[CurriculumFillBlanksWordSnapshot, ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[CurriculumFillBlanksConceptCriterionSnapshot, ...]
    partial_explanation: str | None = None
    kind: Literal['fill_blanks'] = 'fill_blanks'

    def __post_init__(self) -> None:
        for name in (
            'key',
            'prompt',
            'content_language',
            'correct_explanation',
            'incorrect_explanation',
        ):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        blank_keys = tuple(blank.key for blank in self.blanks)
        referenced = tuple(
            segment.blank_key
            for segment in self.segments
            if segment.blank_key is not None
        )
        bank_keys = tuple(word.key for word in self.bank)
        concept_ids = tuple(item.concept_id for item in self.concept_criteria)
        if (
            self.kind != 'fill_blanks'
            or not self.blanks
            or len(blank_keys) != len(set(blank_keys))
            or referenced != blank_keys
            or len(bank_keys) != len(set(bank_keys))
            or (len(self.blanks) >= 2) != (self.partial_explanation is not None)
            or not self.concept_criteria
            or len(concept_ids) != len(set(concept_ids))
            or any(
                not set(item.blank_keys) <= set(blank_keys)
                for item in self.concept_criteria
            )
        ):
            raise ValidationError

from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .fill_blanks_bank_word import FillBlanksBankWord
from .fill_blanks_blank import FillBlanksBlank
from .fill_blanks_concept_criterion import FillBlanksConceptCriterion
from .fill_blanks_segment import FillBlanksSegment


@structure
class FillBlanksQuestion:
    key: str
    prompt: str
    content_language: str
    segments: tuple[FillBlanksSegment, ...]
    blanks: tuple[FillBlanksBlank, ...]
    bank: tuple[FillBlanksBankWord, ...]
    correct_explanation: str
    incorrect_explanation: str
    concept_criteria: tuple[FillBlanksConceptCriterion, ...]
    partial_explanation: str | None = None
    kind: Literal['fill_blanks'] = 'fill_blanks'

    def __post_init__(self) -> None:
        if self.kind != 'fill_blanks':
            raise InvalidActivityError

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
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        if self.partial_explanation is not None:
            object.__setattr__(
                self,
                'partial_explanation',
                NonEmptyText.create(
                    self.partial_explanation, error_type=InvalidActivityError
                ).value,
            )
        blank_keys = tuple(blank.key for blank in self.blanks)
        if (
            not self.blanks
            or len(blank_keys) != len(set(blank_keys))
            or (len(self.blanks) >= 2) != (self.partial_explanation is not None)
        ):
            raise InvalidActivityError

        referenced = tuple(
            segment.blank_key
            for segment in self.segments
            if segment.blank_key is not None
        )
        if referenced != blank_keys:
            raise InvalidActivityError

        bank_keys = tuple(word.key for word in self.bank)
        if len(bank_keys) != len(set(bank_keys)):
            raise InvalidActivityError

        if not self.concept_criteria:
            raise InvalidActivityError

        concept_ids = tuple(item.concept_id for item in self.concept_criteria)
        if len(concept_ids) != len(set(concept_ids)) or any(
            not set(item.blank_keys) <= set(blank_keys)
            for item in self.concept_criteria
        ):
            raise InvalidActivityError

        if not self._has_complete_solution():
            raise InvalidActivityError

    def _has_complete_solution(self) -> bool:
        """Match every blank to a distinct bank occurrence it accepts."""
        candidates = tuple(
            tuple(
                index
                for index, word in enumerate(self.bank)
                if word.word in blank.accepted_words
            )
            for blank in self.blanks
        )
        owner: dict[int, int] = {}

        def assign(blank_index: int, seen: set[int]) -> bool:
            for word_index in candidates[blank_index]:
                if word_index in seen:
                    continue

                seen.add(word_index)
                if word_index not in owner or assign(owner[word_index], seen):
                    owner[word_index] = blank_index
                    return True
            return False

        return all(assign(index, set()) for index in range(len(self.blanks)))

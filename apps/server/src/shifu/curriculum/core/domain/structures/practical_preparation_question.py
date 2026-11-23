from decimal import Decimal
from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures.choice_concept_criterion import (
    ChoiceConceptCriterion,
)
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .practical_preparation_criterion import PracticeCriterion
from .practical_preparation_insufficiency_rule import PracticeInsufficiencyRule
from .practical_preparation_record import PracticePhotoRecord
from .practical_preparation_reference import PracticeReference

_DIFFICULTIES = ('easy', 'medium', 'hard')


@structure
class PracticalPreparationQuestion:
    key: str
    prompt: str
    guidance: tuple[str, ...]
    references: tuple[PracticeReference, ...]
    difficulty: str
    records: tuple[PracticePhotoRecord, ...]
    criteria: tuple[PracticeCriterion, ...]
    insufficiency_rules: tuple[PracticeInsufficiencyRule, ...]
    concept_criteria: tuple[ChoiceConceptCriterion, ...]
    kind: Literal['practical_preparation'] = 'practical_preparation'

    def __post_init__(self) -> None:
        for name in ('key', 'prompt'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        for guidance in self.guidance:
            NonEmptyText.create(guidance, error_type=InvalidActivityError)

        record_keys = tuple(record.key for record in self.records)
        criterion_keys = tuple(criterion.key for criterion in self.criteria)
        comment_keys = tuple(
            level.comment_key
            for criterion in self.criteria
            for level in criterion.levels
        )
        if (
            self.kind != 'practical_preparation'
            or self.difficulty not in _DIFFICULTIES
            or not 1 <= len(self.records) <= 5
            or len(record_keys) != len(set(record_keys))
            or not self.criteria
            or len(criterion_keys) != len(set(criterion_keys))
            or len(comment_keys) != len(set(comment_keys))
            or sum((criterion.weight for criterion in self.criteria), start=Decimal(0))
            != Decimal(100)
            or not self.concept_criteria
            or len({item.concept_id for item in self.concept_criteria})
            != len(self.concept_criteria)
        ):
            raise InvalidActivityError

        for rule in self.insufficiency_rules:
            if rule.record_key not in record_keys or not set(
                rule.criterion_keys
            ).issubset(criterion_keys):
                raise InvalidActivityError

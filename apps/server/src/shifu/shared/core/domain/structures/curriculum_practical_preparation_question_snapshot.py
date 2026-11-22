from decimal import Decimal
from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.curriculum_choice_concept_criterion_snapshot import (
    CurriculumChoiceConceptCriterionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_practical_preparation_criterion_snapshot import (
    CurriculumPracticalPreparationCriterionSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_practical_preparation_insufficiency_rule_snapshot import (
    CurriculumPracticalPreparationInsufficiencyRuleSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_practical_preparation_record_snapshot import (
    CurriculumPracticalPreparationRecordSnapshot,
)
from shifu.shared.core.domain.structures.curriculum_practical_preparation_reference_snapshot import (
    CurriculumPracticalPreparationReferenceSnapshot,
)
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

_DIFFICULTIES = ('easy', 'medium', 'hard')


@structure
class CurriculumPracticalPreparationQuestionSnapshot:
    key: str
    kind: Literal['practical_preparation']
    prompt: str
    guidance: tuple[str, ...]
    references: tuple[CurriculumPracticalPreparationReferenceSnapshot, ...]
    difficulty: str
    records: tuple[CurriculumPracticalPreparationRecordSnapshot, ...]
    criteria: tuple[CurriculumPracticalPreparationCriterionSnapshot, ...]
    insufficiency_rules: tuple[
        CurriculumPracticalPreparationInsufficiencyRuleSnapshot, ...
    ]
    concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        for name in ('key', 'prompt'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=ValidationError
                ).value,
            )
        for guidance in self.guidance:
            NonEmptyText.create(guidance, error_type=ValidationError)

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
            raise ValidationError

        for rule in self.insufficiency_rules:
            if rule.record_key not in record_keys or not set(
                rule.criterion_keys
            ).issubset(criterion_keys):
                raise ValidationError

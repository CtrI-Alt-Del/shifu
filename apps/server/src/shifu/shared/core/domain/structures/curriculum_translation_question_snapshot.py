from typing import Literal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_code_concept_criterion_snapshot import (
    CurriculumCodeConceptCriterionSnapshot,
)


@structure
class CurriculumTranslationQuestionSnapshot:
    key: str
    prompt: str
    source_language: str
    target_language: str
    source_text: str
    reference_translations: tuple[str, ...]
    concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...]
    kind: Literal['translation'] = 'translation'

    def __post_init__(self) -> None:
        for value in (
            self.key,
            self.prompt,
            self.source_language,
            self.target_language,
            self.source_text,
        ):
            NonEmptyText.create(value, error_type=ValidationError)
        if self.kind != 'translation' or not self.reference_translations:
            raise ValidationError

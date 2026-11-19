from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_code_concept_criterion_snapshot import (
    CurriculumCodeConceptCriterionSnapshot,
)
from .curriculum_translation_rubric_criterion_snapshot import (
    CurriculumTranslationRubricCriterionSnapshot,
)


@structure
class TranslationRubricAssessmentInput:
    question_kind: str
    source_text: str
    source_language: str
    target_language: str
    reference_translations: tuple[str, ...]
    submitted_text: str
    rubric_criteria: tuple[CurriculumTranslationRubricCriterionSnapshot, ...]
    concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        for value in (
            self.question_kind,
            self.source_text,
            self.source_language,
            self.target_language,
            self.submitted_text,
        ):
            NonEmptyText.create(value, error_type=ValidationError)
        for translation in self.reference_translations:
            NonEmptyText.create(translation, error_type=ValidationError)
        if not self.rubric_criteria:
            raise ValidationError

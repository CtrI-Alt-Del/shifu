from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_code_concept_criterion_snapshot import (
    CurriculumCodeConceptCriterionSnapshot,
)
from .curriculum_code_rubric_criterion_snapshot import (
    CurriculumCodeRubricCriterionSnapshot,
)


@structure
class CodeRubricAssessmentInput:
    question_kind: str
    prompt: str
    project_files: tuple[tuple[str, str], ...]
    submitted_paths: tuple[str, ...]
    rubric_criteria: tuple[CurriculumCodeRubricCriterionSnapshot, ...]
    concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...]

    def __post_init__(self) -> None:
        NonEmptyText.create(self.question_kind, error_type=ValidationError)
        NonEmptyText.create(self.prompt, error_type=ValidationError)
        paths = tuple(path for path, _ in self.project_files)
        if (
            not paths
            or len(paths) != len(set(paths))
            or not set(self.submitted_paths).issubset(paths)
            or len(self.submitted_paths) != len(set(self.submitted_paths))
            or not self.rubric_criteria
        ):
            raise ValidationError

from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.structure import structure
from shifu.shared.core.domain.validation import require_non_empty

from .curriculum_choice_part_snapshot import CurriculumChoicePartSnapshot
from .curriculum_choice_question_snapshot import CurriculumChoiceQuestionSnapshot
from .curriculum_code_rubric_part_snapshot import CurriculumCodeRubricPartSnapshot
from .curriculum_javascript_stdin_question_snapshot import (
    CurriculumJavascriptStdinQuestionSnapshot,
)


@structure
class CurriculumLearningActivitySnapshot:
    id: str
    competency_id: str
    difficulty: str
    title: str
    questions: tuple[
        CurriculumChoiceQuestionSnapshot | CurriculumJavascriptStdinQuestionSnapshot,
        ...,
    ]
    parts: tuple[CurriculumChoicePartSnapshot | CurriculumCodeRubricPartSnapshot, ...]
    required_concept_ids: tuple[str, ...]
    activity_type: str
    schema_version: int
    revision: str
    diagnostic_revision: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.id,
            self.competency_id,
            self.difficulty,
            self.title,
            self.revision,
        ):
            require_non_empty(value, ValidationError)
        if self.diagnostic_revision is not None:
            require_non_empty(self.diagnostic_revision, ValidationError)
        question_keys = tuple(question.key for question in self.questions)
        part_keys = tuple(part.question_key for part in self.parts)
        if (
            self.activity_type not in {'learning', 'diagnostic'}
            or self.schema_version != 1
            or (
                not 3 <= len(self.questions) <= 5
                if self.activity_type == 'learning'
                else not self.questions
            )
            or len(question_keys) != len(set(question_keys))
            or len(part_keys) != len(set(part_keys))
            or set(question_keys) != set(part_keys)
            or sum((part.weight_percentage for part in self.parts), start=Decimal(0))
            != Decimal(100)
        ):
            raise ValidationError
        parts = {part.question_key: part for part in self.parts}
        for question in self.questions:
            if isinstance(
                question, CurriculumJavascriptStdinQuestionSnapshot
            ) != isinstance(parts[question.key], CurriculumCodeRubricPartSnapshot):
                raise ValidationError

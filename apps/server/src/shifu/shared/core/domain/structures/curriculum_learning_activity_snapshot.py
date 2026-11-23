from decimal import Decimal

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure

from .curriculum_choice_part_snapshot import CurriculumChoicePartSnapshot
from .curriculum_choice_question_snapshot import CurriculumChoiceQuestionSnapshot
from .curriculum_image_choice_question_snapshot import (
    CurriculumImageChoiceQuestionSnapshot,
)
from .curriculum_ordering_question_snapshot import CurriculumOrderingQuestionSnapshot
from .curriculum_code_rubric_part_snapshot import CurriculumCodeRubricPartSnapshot
from .curriculum_fill_blanks_question_snapshot import (
    CurriculumFillBlanksQuestionSnapshot,
)
from .curriculum_javascript_stdin_question_snapshot import (
    CurriculumJavascriptStdinQuestionSnapshot,
)
from .curriculum_pair_matching_question_snapshot import (
    CurriculumPairMatchingQuestionSnapshot,
)
from .curriculum_practical_preparation_question_snapshot import (
    CurriculumPracticalPreparationQuestionSnapshot,
)
from .curriculum_react_question_snapshot import CurriculumReactQuestionSnapshot
from .curriculum_html_css_js_question_snapshot import (
    CurriculumHtmlCssJsQuestionSnapshot,
)
from .curriculum_react_fastify_question_snapshot import (
    CurriculumReactFastifyQuestionSnapshot,
)
from .curriculum_translation_question_snapshot import (
    CurriculumTranslationQuestionSnapshot,
)
from .curriculum_translation_rubric_part_snapshot import (
    CurriculumTranslationRubricPartSnapshot,
)


@structure
class CurriculumLearningActivitySnapshot:
    id: str
    competency_id: str
    difficulty: str
    title: str
    questions: tuple[
        CurriculumChoiceQuestionSnapshot
        | CurriculumOrderingQuestionSnapshot
        | CurriculumJavascriptStdinQuestionSnapshot
        | CurriculumReactQuestionSnapshot
        | CurriculumHtmlCssJsQuestionSnapshot
        | CurriculumReactFastifyQuestionSnapshot
        | CurriculumFillBlanksQuestionSnapshot
        | CurriculumTranslationQuestionSnapshot
        | CurriculumPairMatchingQuestionSnapshot
        | CurriculumImageChoiceQuestionSnapshot
        | CurriculumPracticalPreparationQuestionSnapshot,
        ...,
    ]
    parts: tuple[
        CurriculumChoicePartSnapshot
        | CurriculumCodeRubricPartSnapshot
        | CurriculumTranslationRubricPartSnapshot,
        ...,
    ]
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
            NonEmptyText.create(value, error_type=ValidationError)
        if self.diagnostic_revision is not None:
            NonEmptyText.create(self.diagnostic_revision, error_type=ValidationError)
        question_keys = tuple(question.key for question in self.questions)
        part_keys = tuple(part.question_key for part in self.parts)
        if (
            self.activity_type not in {'learning', 'diagnostic'}
            or self.schema_version != 1
            or (
                not self._has_valid_question_count()
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
            self._validate_question_part(
                question, parts[question.key], self.activity_type
            )
        if any(
            isinstance(question, CurriculumTranslationQuestionSnapshot)
            for question in self.questions
        ) and any(
            isinstance(
                question,
                (
                    CurriculumJavascriptStdinQuestionSnapshot,
                    CurriculumReactQuestionSnapshot,
                    CurriculumHtmlCssJsQuestionSnapshot,
                    CurriculumReactFastifyQuestionSnapshot,
                ),
            )
            for question in self.questions
        ):
            raise ValidationError

    def _has_valid_question_count(self) -> bool:
        if any(
            isinstance(question, CurriculumPracticalPreparationQuestionSnapshot)
            for question in self.questions
        ):
            return len(self.questions) == 1

        return 3 <= len(self.questions) <= 5

    @staticmethod
    def _validate_question_part(
        question: object, part: object, activity_type: str
    ) -> None:
        requires_code_rubric = isinstance(
            question,
            (
                CurriculumJavascriptStdinQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
                CurriculumHtmlCssJsQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
            ),
        )
        if requires_code_rubric != isinstance(part, CurriculumCodeRubricPartSnapshot):
            raise ValidationError
        if isinstance(
            question,
            (
                CurriculumOrderingQuestionSnapshot,
                CurriculumFillBlanksQuestionSnapshot,
                CurriculumPairMatchingQuestionSnapshot,
                CurriculumImageChoiceQuestionSnapshot,
                CurriculumPracticalPreparationQuestionSnapshot,
            ),
        ) and not isinstance(part, CurriculumChoicePartSnapshot):
            raise ValidationError
        requires_translation_rubric = isinstance(
            question, CurriculumTranslationQuestionSnapshot
        )
        if requires_translation_rubric != isinstance(
            part, CurriculumTranslationRubricPartSnapshot
        ):
            raise ValidationError
        if activity_type == 'diagnostic' and isinstance(
            question,
            (
                CurriculumOrderingQuestionSnapshot,
                CurriculumFillBlanksQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
                CurriculumHtmlCssJsQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
                CurriculumTranslationQuestionSnapshot,
                CurriculumPairMatchingQuestionSnapshot,
                CurriculumImageChoiceQuestionSnapshot,
                CurriculumPracticalPreparationQuestionSnapshot,
            ),
        ):
            raise ValidationError

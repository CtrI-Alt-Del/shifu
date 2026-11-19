from shifu.curriculum.core.domain.structures import (
    ActivityQuestion,
    JavascriptStdinQuestion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    ReactQuestion,
    HtmlCssJsQuestion,
    ReactFastifyQuestion,
    OrderingQuestion,
    TranslationQuestion,
    TranslationRubricEvaluationPart,
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText

_CODE_QUESTION_TYPES = (
    JavascriptStdinQuestion,
    ReactQuestion,
    HtmlCssJsQuestion,
    ReactFastifyQuestion,
)


def _validate_ai_graded_rubric_pairing(
    questions: tuple[ActivityQuestion, ...],
    evaluation_rule: EvaluationRule,
    question_keys: set[str],
    part_keys: set[str],
) -> None:
    has_code_question = any(
        isinstance(question, _CODE_QUESTION_TYPES) for question in questions
    )
    has_translation_question = any(
        isinstance(question, TranslationQuestion) for question in questions
    )
    if not (has_code_question or has_translation_question):
        return

    if len(part_keys) != len(evaluation_rule.parts) or part_keys != question_keys:
        raise InvalidActivityError

    if has_code_question and has_translation_question:
        raise InvalidActivityError

    parts = {part.question_key: part for part in evaluation_rule.parts}
    for question in questions:
        part = parts[question.key]
        if isinstance(question, _CODE_QUESTION_TYPES) != isinstance(
            part, CodeRubricEvaluationPart
        ):
            raise InvalidActivityError
        if isinstance(question, TranslationQuestion) != isinstance(
            part, TranslationRubricEvaluationPart
        ):
            raise InvalidActivityError


@entity
class Activity:
    id: str
    competency_id: str
    activity_type: ActivityType
    difficulty: ActivityDifficulty
    title: str
    objective: str
    questions: tuple[ActivityQuestion, ...]
    evaluation_rule: EvaluationRule
    required_concept_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.title = NonEmptyText.create(
            self.title, error_type=InvalidActivityError
        ).value
        self.objective = NonEmptyText.create(
            self.objective, error_type=InvalidActivityError
        ).value
        if not self.questions:
            raise InvalidActivityError

        question_keys = {question.key for question in self.questions}
        part_keys = {part.question_key for part in self.evaluation_rule.parts}
        if len(question_keys) != len(self.questions) or not part_keys.issubset(
            question_keys
        ):
            raise InvalidActivityError

        _validate_ai_graded_rubric_pairing(
            self.questions, self.evaluation_rule, question_keys, part_keys
        )

        if self.activity_type == ActivityType.DIAGNOSTIC and any(
            isinstance(
                question,
                (
                    ReactQuestion,
                    HtmlCssJsQuestion,
                    ReactFastifyQuestion,
                    OrderingQuestion,
                    TranslationQuestion,
                ),
            )
            for question in self.questions
        ):
            raise InvalidActivityError

        if _has_invalid_ordering_part(self.questions, self.evaluation_rule.parts):
            raise InvalidActivityError

        if len(self.required_concept_ids) != len(set(self.required_concept_ids)):
            raise InvalidActivityError

        if _has_required_concept_overlap(self.questions, self.required_concept_ids):
            raise InvalidActivityError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        competency_id: str,
        activity_type: ActivityType,
        difficulty: ActivityDifficulty,
        title: str,
        objective: str,
        questions: tuple[ActivityQuestion, ...],
        evaluation_rule: EvaluationRule,
        required_concept_ids: tuple[str, ...] = (),
    ) -> 'Activity':
        return cls(
            id=id,
            competency_id=competency_id,
            activity_type=activity_type,
            difficulty=difficulty,
            title=title,
            objective=objective,
            questions=questions,
            evaluation_rule=evaluation_rule,
            required_concept_ids=required_concept_ids,
        )


def _has_invalid_ordering_part(
    questions: tuple[ActivityQuestion, ...],
    parts: tuple[object, ...],
) -> bool:
    parts_by_key = {
        part.question_key: part
        for part in parts
        if isinstance(part, CorrectnessEvaluationPart | CodeRubricEvaluationPart)
    }
    return any(
        isinstance(question, OrderingQuestion)
        and not isinstance(parts_by_key.get(question.key), CorrectnessEvaluationPart)
        for question in questions
    )


def _has_required_concept_overlap(
    questions: tuple[ActivityQuestion, ...],
    required_concept_ids: tuple[str, ...],
) -> bool:
    assessed = {
        criterion.concept_id
        for question in questions
        for criterion in getattr(question, 'concept_criteria', ())
    }
    return bool(assessed.intersection(required_concept_ids))

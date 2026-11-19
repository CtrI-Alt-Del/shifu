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
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


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

        if _has_invalid_code_parts(
            self.questions, self.evaluation_rule.parts, question_keys, part_keys
        ):
            raise InvalidActivityError

        if self.activity_type == ActivityType.DIAGNOSTIC and any(
            isinstance(
                question,
                (
                    ReactQuestion,
                    HtmlCssJsQuestion,
                    ReactFastifyQuestion,
                    OrderingQuestion,
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


def _has_invalid_code_parts(
    questions: tuple[ActivityQuestion, ...],
    parts: tuple[object, ...],
    question_keys: set[str],
    part_keys: set[str],
) -> bool:
    code_questions = tuple(
        question
        for question in questions
        if isinstance(
            question,
            (
                JavascriptStdinQuestion,
                ReactQuestion,
                HtmlCssJsQuestion,
                ReactFastifyQuestion,
            ),
        )
    )
    if not code_questions:
        return False
    if len(part_keys) != len(parts) or part_keys != question_keys:
        return True

    parts_by_key = {
        part.question_key: part
        for part in parts
        if isinstance(part, CorrectnessEvaluationPart | CodeRubricEvaluationPart)
    }
    return any(
        isinstance(
            question,
            (
                JavascriptStdinQuestion,
                ReactQuestion,
                HtmlCssJsQuestion,
                ReactFastifyQuestion,
            ),
        )
        != isinstance(parts_by_key.get(question.key), CodeRubricEvaluationPart)
        for question in questions
    )

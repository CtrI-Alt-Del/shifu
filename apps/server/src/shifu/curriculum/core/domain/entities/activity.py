from shifu.curriculum.core.domain.structures import (
    ActivityQuestion,
    JavascriptStdinQuestion,
    CodeRubricEvaluationPart,
    EvaluationRule,
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

        if any(
            isinstance(question, JavascriptStdinQuestion) for question in self.questions
        ):
            if (
                len(part_keys) != len(self.evaluation_rule.parts)
                or part_keys != question_keys
            ):
                raise InvalidActivityError

            parts = {part.question_key: part for part in self.evaluation_rule.parts}
            for question in self.questions:
                part = parts[question.key]
                if isinstance(question, JavascriptStdinQuestion) != isinstance(
                    part, CodeRubricEvaluationPart
                ):
                    raise InvalidActivityError

        if len(self.required_concept_ids) != len(set(self.required_concept_ids)):
            raise InvalidActivityError

        assessed = {
            criterion.concept_id
            for question in self.questions
            for criterion in getattr(question, 'concept_criteria', ())
        }
        if assessed.intersection(self.required_concept_ids):
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

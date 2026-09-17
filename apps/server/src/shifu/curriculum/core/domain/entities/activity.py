from shifu.curriculum.core.domain.structures import (
    ActivityQuestion,
    EvaluationRule,
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_non_empty


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

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, InvalidActivityError)
        self.objective = require_non_empty(self.objective, InvalidActivityError)
        if not self.questions:
            raise InvalidActivityError
        question_keys = {question.key for question in self.questions}
        part_keys = {part.question_key for part in self.evaluation_rule.parts}
        if not part_keys.issubset(question_keys):
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
        )

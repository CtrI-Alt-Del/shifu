from shifu.curriculum.core.domain.structures import (
    ActivityQuestion,
    EvaluationRule,
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.shared.core.domain.entities import entity


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

from typing import cast

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ActivityQuestion,
    EvaluationRule,
)
from shifu.curriculum.database.sqlalchemy.models import ActivityModel
from shifu.shared.database.sqlalchemy.serialization import (
    deserialize_value,
    serialize_value,
)


class ActivityMapper:
    @staticmethod
    def to_domain(model: ActivityModel) -> Activity:
        return Activity(
            id=model.id,
            competency_id=model.competency_id,
            activity_type=ActivityType(model.activity_type),
            difficulty=ActivityDifficulty(model.difficulty),
            title=model.title,
            objective=model.objective,
            questions=cast(
                'tuple[ActivityQuestion, ...]',
                deserialize_value(model.questions, tuple[ActivityQuestion, ...]),
            ),
            evaluation_rule=cast(
                'EvaluationRule',
                deserialize_value(model.evaluation_rule, EvaluationRule),
            ),
        )

    @staticmethod
    def to_model(activity: Activity) -> ActivityModel:
        return ActivityModel(
            id=activity.id,
            competency_id=activity.competency_id,
            activity_type=activity.activity_type.value,
            difficulty=activity.difficulty.value,
            title=activity.title,
            objective=activity.objective,
            questions=serialize_value(activity.questions),
            evaluation_rule=serialize_value(activity.evaluation_rule),
        )

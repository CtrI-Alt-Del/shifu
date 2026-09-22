from typing import cast

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    CodeQuestion,
    CorrectnessEvaluationPart,
    EvaluationRule,
    MultipleSelectionQuestion,
    QualitativeEvaluationPart,
    SingleChoiceQuestion,
    TestCasesEvaluationPart,
)
from shifu.curriculum.database.sqlalchemy.models import ActivityModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


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
                'tuple[SingleChoiceQuestion | MultipleSelectionQuestion | CodeQuestion, ...]',
                Serialization.deserialize_value(
                    model.questions,
                    tuple[
                        SingleChoiceQuestion | MultipleSelectionQuestion | CodeQuestion,
                        ...,
                    ],
                ),
            ),
            evaluation_rule=EvaluationRule(
                parts=cast(
                    'tuple[CorrectnessEvaluationPart | TestCasesEvaluationPart | QualitativeEvaluationPart, ...]',
                    Serialization.deserialize_value(
                        cast('dict[str, object]', model.evaluation_rule)['parts'],
                        tuple[
                            CorrectnessEvaluationPart
                            | TestCasesEvaluationPart
                            | QualitativeEvaluationPart,
                            ...,
                        ],
                    ),
                )
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
            questions=Serialization.serialize_value(activity.questions),
            evaluation_rule=Serialization.serialize_value(activity.evaluation_rule),
        )

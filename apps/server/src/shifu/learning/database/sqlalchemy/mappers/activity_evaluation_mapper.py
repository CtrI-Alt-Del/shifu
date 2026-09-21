from typing import cast

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import EvaluationPartResult
from shifu.learning.database.sqlalchemy.models import ActivityEvaluationModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class ActivityEvaluationMapper:
    @staticmethod
    def to_domain(model: ActivityEvaluationModel) -> ActivityEvaluation:
        return ActivityEvaluation(
            id=model.id,
            attempt_id=model.attempt_id,
            status=ActivityEvaluationStatus(model.status),
            parts=cast(
                'tuple[EvaluationPartResult, ...]',
                Serialization.deserialize_value(
                    model.parts, tuple[EvaluationPartResult, ...]
                ),
            ),
            started_at=model.started_at,
            score=model.score,
            failure_code=model.failure_code,
            completed_at=model.completed_at,
            effect_applied_at=model.effect_applied_at,
        )

    @staticmethod
    def to_model(evaluation: ActivityEvaluation) -> ActivityEvaluationModel:
        return ActivityEvaluationModel(
            id=evaluation.id,
            attempt_id=evaluation.attempt_id,
            status=evaluation.status.value,
            parts=Serialization.serialize_value(evaluation.parts),
            started_at=evaluation.started_at,
            score=evaluation.score,
            failure_code=evaluation.failure_code,
            completed_at=evaluation.completed_at,
            effect_applied_at=evaluation.effect_applied_at,
        )

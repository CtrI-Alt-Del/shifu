from typing import cast

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures import (
    ChoiceEvaluationResult,
    CodeEvaluationResult,
    EvaluationPartResult,
    QualitativeEvaluationResult,
)
from shifu.learning.database.sqlalchemy.models import ActivityEvaluationModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class ActivityEvaluationMapper:
    @staticmethod
    def _deserialize_parts(value: object) -> tuple[EvaluationPartResult, ...]:
        serialized_parts = cast('list[dict[str, object]]', value)
        parts: list[EvaluationPartResult] = []
        for serialized_part in serialized_parts:
            if 'is_correct' in serialized_part:
                part_type = ChoiceEvaluationResult
            elif 'cases' in serialized_part:
                part_type = CodeEvaluationResult
            elif 'criteria' in serialized_part:
                part_type = QualitativeEvaluationResult
            else:
                raise TypeError('Unknown evaluation part serialization')
            part = Serialization.deserialize_value(serialized_part, part_type)
            parts.append(cast('EvaluationPartResult', part))
        return tuple(parts)

    @staticmethod
    def to_domain(model: ActivityEvaluationModel) -> ActivityEvaluation:
        return ActivityEvaluation(
            id=model.id,
            attempt_id=model.attempt_id,
            status=ActivityEvaluationStatus(model.status),
            parts=ActivityEvaluationMapper._deserialize_parts(model.parts),
            started_at=model.started_at,
            score=model.score,
            failure_code=model.failure_code,
            completed_at=model.completed_at,
            effect_applied_at=model.effect_applied_at,
            run_id=model.run_id,
            progress_before=model.progress_before,
            progress_after=model.progress_after,
            status_before=(
                CompetencyProgressStatus(model.status_before)
                if model.status_before is not None
                else None
            ),
            status_after=(
                CompetencyProgressStatus(model.status_after)
                if model.status_after is not None
                else None
            ),
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
            run_id=evaluation.run_id,
            progress_before=evaluation.progress_before,
            progress_after=evaluation.progress_after,
            status_before=(
                evaluation.status_before.value
                if evaluation.status_before is not None
                else None
            ),
            status_after=(
                evaluation.status_after.value
                if evaluation.status_after is not None
                else None
            ),
        )

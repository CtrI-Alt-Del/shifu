from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.database.sqlalchemy.mappers import ActivityEvaluationMapper
from shifu.learning.database.sqlalchemy.models import (
    ActivityAttemptModel,
    ActivityEvaluationModel,
)


class SqlalchemyActivityEvaluationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, evaluation_id: str) -> ActivityEvaluation | None:
        model = self._session.scalar(
            select(ActivityEvaluationModel).where(
                ActivityEvaluationModel.id == evaluation_id
            )
        )
        return ActivityEvaluationMapper.to_domain(model) if model is not None else None

    def find_by_attempt_id(self, attempt_id: str) -> ActivityEvaluation | None:
        model = self._session.scalar(
            select(ActivityEvaluationModel).where(
                ActivityEvaluationModel.attempt_id == attempt_id
            )
        )
        return ActivityEvaluationMapper.to_domain(model) if model is not None else None

    def find_unresolved_by_skill_experience_id(
        self,
        skill_experience_id: str,
    ) -> ActivityEvaluation | None:
        model = self._session.scalar(
            select(ActivityEvaluationModel)
            .join(
                ActivityAttemptModel,
                ActivityAttemptModel.id == ActivityEvaluationModel.attempt_id,
            )
            .where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityEvaluationModel.status.in_(
                    (
                        ActivityEvaluationStatus.PENDING.value,
                        ActivityEvaluationStatus.FAILED.value,
                    )
                ),
            )
            .order_by(ActivityEvaluationModel.started_at)
        )
        return ActivityEvaluationMapper.to_domain(model) if model is not None else None

    def find_many_by_skill_experience_id_and_activity_id(
        self,
        skill_experience_id: str,
        activity_id: str,
    ) -> list[ActivityEvaluation]:
        models = self._session.scalars(
            select(ActivityEvaluationModel)
            .join(
                ActivityAttemptModel,
                ActivityAttemptModel.id == ActivityEvaluationModel.attempt_id,
            )
            .where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityAttemptModel.activity_id == activity_id,
            )
            .order_by(ActivityAttemptModel.submitted_at)
        ).all()
        return [ActivityEvaluationMapper.to_domain(model) for model in models]

    def find_many_by_attempt_ids(
        self,
        attempt_ids: tuple[str, ...],
    ) -> list[ActivityEvaluation]:
        if not attempt_ids:
            return []
        models = self._session.scalars(
            select(ActivityEvaluationModel).where(
                ActivityEvaluationModel.attempt_id.in_(attempt_ids)
            )
        ).all()
        return [ActivityEvaluationMapper.to_domain(model) for model in models]

    def add(self, evaluation: ActivityEvaluation) -> None:
        self._session.add(ActivityEvaluationMapper.to_model(evaluation))

    def add_many(self, evaluations: list[ActivityEvaluation]) -> None:
        self._session.add_all(
            [
                ActivityEvaluationMapper.to_model(evaluation)
                for evaluation in evaluations
            ]
        )
        self._session.flush()

    def update(self, evaluation: ActivityEvaluation) -> None:
        self._session.merge(ActivityEvaluationMapper.to_model(evaluation))

    def remove_all(self) -> None:
        self._session.execute(delete(ActivityEvaluationModel))

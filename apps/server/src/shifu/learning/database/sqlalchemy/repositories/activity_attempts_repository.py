from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.database.sqlalchemy.mappers import ActivityAttemptMapper
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel


class SqlalchemyActivityAttemptsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, attempt_id: str) -> ActivityAttempt | None:
        model = self._session.scalar(
            select(ActivityAttemptModel).where(ActivityAttemptModel.id == attempt_id)
        )
        return ActivityAttemptMapper.to_domain(model) if model is not None else None

    def find_many_by_skill_experience_id_and_activity_id_and_kind(
        self,
        skill_experience_id: str,
        activity_id: str,
        kind: ActivityAttemptKind,
    ) -> list[ActivityAttempt]:
        models = self._session.scalars(
            select(ActivityAttemptModel)
            .where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityAttemptModel.activity_id == activity_id,
                ActivityAttemptModel.kind == kind.value,
            )
            .order_by(ActivityAttemptModel.submitted_at)
        ).all()
        return [ActivityAttemptMapper.to_domain(model) for model in models]

    def find_many_by_skill_experience_id(
        self,
        skill_experience_id: str,
    ) -> list[ActivityAttempt]:
        models = self._session.scalars(
            select(ActivityAttemptModel)
            .where(ActivityAttemptModel.skill_experience_id == skill_experience_id)
            .order_by(ActivityAttemptModel.submitted_at)
        ).all()
        return [ActivityAttemptMapper.to_domain(model) for model in models]

    def find_many_by_skill_experience_id_and_activity_id(
        self,
        skill_experience_id: str,
        activity_id: str,
    ) -> list[ActivityAttempt]:
        models = self._session.scalars(
            select(ActivityAttemptModel)
            .where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityAttemptModel.activity_id == activity_id,
            )
            .order_by(ActivityAttemptModel.submitted_at)
        ).all()
        return [ActivityAttemptMapper.to_domain(model) for model in models]

    def add(self, attempt: ActivityAttempt) -> None:
        self._session.add(ActivityAttemptMapper.to_model(attempt))

    def add_many(self, attempts: list[ActivityAttempt]) -> None:
        self._session.add_all(
            [ActivityAttemptMapper.to_model(attempt) for attempt in attempts]
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(ActivityAttemptModel))

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.learning.database.sqlalchemy.mappers import ActivityAttemptMapper
from shifu.learning.database.sqlalchemy.models import (
    ActivityAttemptModel,
    GoalModel,
    SkillExperienceModel,
    ActivityEvaluationModel,
)


class SqlalchemyActivityAttemptsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, attempt_id: str) -> ActivityAttempt | None:
        model = self._session.scalar(
            select(ActivityAttemptModel).where(ActivityAttemptModel.id == attempt_id)
        )
        return ActivityAttemptMapper.to_domain(model) if model is not None else None

    def find_account_id_by_attempt_id(self, attempt_id: str) -> str | None:
        return self._session.scalar(
            select(GoalModel.account_id)
            .join(
                SkillExperienceModel,
                SkillExperienceModel.goal_id == GoalModel.id,
            )
            .join(
                ActivityAttemptModel,
                ActivityAttemptModel.skill_experience_id == SkillExperienceModel.id,
            )
            .where(ActivityAttemptModel.id == attempt_id)
        )

    def find_ids_by_account_id(self, account_id: str) -> list[str]:
        return list(
            self._session.scalars(
                select(ActivityAttemptModel.id)
                .join(
                    SkillExperienceModel,
                    SkillExperienceModel.id == ActivityAttemptModel.skill_experience_id,
                )
                .join(GoalModel, GoalModel.id == SkillExperienceModel.goal_id)
                .where(GoalModel.account_id == account_id)
            ).all()
        )

    def find_by_skill_experience_id_and_submission_key(
        self,
        skill_experience_id: str,
        submission_key: str,
    ) -> ActivityAttempt | None:
        model = self._session.scalar(
            select(ActivityAttemptModel).where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityAttemptModel.submission_key == submission_key,
            )
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

    def find_many_by_skill_experience_id_and_diagnostic_run_id(
        self,
        skill_experience_id: str,
        diagnostic_run_id: str,
    ) -> list[ActivityAttempt]:
        models = self._session.scalars(
            select(ActivityAttemptModel)
            .where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityAttemptModel.diagnostic_run_id == diagnostic_run_id,
            )
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

    def find_many_latest_submitted_at_by_skill_experience_ids(
        self,
        skill_experience_ids: list[str],
    ) -> dict[str, datetime]:
        if not skill_experience_ids:
            return {}

        rows = self._session.execute(
            select(
                ActivityAttemptModel.skill_experience_id,
                func.max(ActivityAttemptModel.submitted_at).label('submitted_at'),
            )
            .where(ActivityAttemptModel.skill_experience_id.in_(skill_experience_ids))
            .group_by(ActivityAttemptModel.skill_experience_id)
        ).all()
        return {row.skill_experience_id: row.submitted_at for row in rows}

    def find_many_evaluated_submitted_at_by_skill_experience_ids(
        self,
        skill_experience_ids: list[str],
        *,
        since: datetime,
    ) -> list[datetime]:
        if not skill_experience_ids:
            return []

        return list(
            self._session.scalars(
                select(ActivityAttemptModel.submitted_at)
                .join(
                    ActivityEvaluationModel,
                    ActivityEvaluationModel.attempt_id == ActivityAttemptModel.id,
                )
                .where(
                    ActivityAttemptModel.skill_experience_id.in_(skill_experience_ids),
                    ActivityAttemptModel.kind.in_(
                        (
                            ActivityAttemptKind.LEARNING.value,
                            ActivityAttemptKind.REVIEW.value,
                        )
                    ),
                    ActivityAttemptModel.submitted_at >= since,
                    ActivityEvaluationModel.status
                    == ActivityEvaluationStatus.COMPLETED.value,
                )
                .order_by(ActivityAttemptModel.submitted_at)
            ).all()
        )

    def add(self, attempt: ActivityAttempt) -> None:
        self._session.add(ActivityAttemptMapper.to_model(attempt))

    def add_many(self, attempts: list[ActivityAttempt]) -> None:
        self._session.add_all(
            [ActivityAttemptMapper.to_model(attempt) for attempt in attempts]
        )

    def remove_diagnostic_by_experience(self, skill_experience_id: str) -> None:
        self._session.execute(
            delete(ActivityAttemptModel).where(
                ActivityAttemptModel.skill_experience_id == skill_experience_id,
                ActivityAttemptModel.kind == ActivityAttemptKind.DIAGNOSTIC.value,
            )
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(ActivityAttemptModel))

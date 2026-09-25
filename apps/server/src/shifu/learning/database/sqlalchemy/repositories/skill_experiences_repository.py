from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.database.sqlalchemy.mappers import SkillExperienceMapper
from shifu.learning.database.sqlalchemy.models import SkillExperienceModel


class SqlalchemySkillExperiencesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, skill_experience_id: str) -> SkillExperience | None:
        model = self._session.scalar(
            select(SkillExperienceModel).where(
                SkillExperienceModel.id == skill_experience_id
            )
        )
        return SkillExperienceMapper.to_domain(model) if model is not None else None

    def find_by_id_for_update(self, skill_experience_id: str) -> SkillExperience | None:
        model = self._session.scalar(
            select(SkillExperienceModel)
            .where(SkillExperienceModel.id == skill_experience_id)
            .with_for_update()
        )
        return SkillExperienceMapper.to_domain(model) if model is not None else None

    def find_by_goal_id_and_skill_id(
        self,
        goal_id: str,
        skill_id: str,
    ) -> SkillExperience | None:
        model = self._session.scalar(
            select(SkillExperienceModel).where(
                SkillExperienceModel.goal_id == goal_id,
                SkillExperienceModel.skill_id == skill_id,
            )
        )
        return SkillExperienceMapper.to_domain(model) if model is not None else None

    def find_many_by_goal_id(self, goal_id: str) -> list[SkillExperience]:
        models = self._session.scalars(
            select(SkillExperienceModel)
            .where(SkillExperienceModel.goal_id == goal_id)
            .order_by(SkillExperienceModel.created_at)
        ).all()
        return [SkillExperienceMapper.to_domain(model) for model in models]

    def count_many_by_goal_ids(self, goal_ids: list[str]) -> dict[str, int]:
        if not goal_ids:
            return {}
        rows = self._session.execute(
            select(
                SkillExperienceModel.goal_id,
                func.count().label('skill_count'),
            )
            .where(SkillExperienceModel.goal_id.in_(goal_ids))
            .group_by(SkillExperienceModel.goal_id)
        ).all()
        return {row.goal_id: row.skill_count for row in rows}

    def add(self, skill_experience: SkillExperience) -> None:
        self._session.add(SkillExperienceMapper.to_model(skill_experience))

    def add_many(self, skill_experiences: list[SkillExperience]) -> None:
        self._session.add_all(
            [
                SkillExperienceMapper.to_model(experience)
                for experience in skill_experiences
            ]
        )
        self._session.flush()

    def update(self, skill_experience: SkillExperience) -> None:
        self._session.merge(SkillExperienceMapper.to_model(skill_experience))

    def remove(self, skill_experience: SkillExperience) -> None:
        self._session.execute(
            delete(SkillExperienceModel).where(
                SkillExperienceModel.id == skill_experience.id
            )
        )

    def remove_all(self) -> None:
        self._session.execute(delete(SkillExperienceModel))

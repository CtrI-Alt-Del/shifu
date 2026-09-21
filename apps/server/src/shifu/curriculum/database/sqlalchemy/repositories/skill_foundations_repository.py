from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.structures import SkillFoundation
from shifu.curriculum.database.sqlalchemy.mappers import SkillFoundationMapper
from shifu.curriculum.database.sqlalchemy.models import SkillFoundationModel


class SqlalchemySkillFoundationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many_by_skill_id(self, skill_id: str) -> list[SkillFoundation]:
        models = self._session.scalars(
            select(SkillFoundationModel).where(
                SkillFoundationModel.skill_id == skill_id
            )
        ).all()
        return [SkillFoundationMapper.to_domain(model) for model in models]

    def find_many_by_foundation_skill_id(
        self,
        foundation_skill_id: str,
    ) -> list[SkillFoundation]:
        models = self._session.scalars(
            select(SkillFoundationModel).where(
                SkillFoundationModel.foundation_skill_id == foundation_skill_id
            )
        ).all()
        return [SkillFoundationMapper.to_domain(model) for model in models]

    def find_all(self) -> list[SkillFoundation]:
        models = self._session.scalars(
            select(SkillFoundationModel).order_by(
                SkillFoundationModel.skill_id,
                SkillFoundationModel.foundation_skill_id,
            )
        ).all()
        return [SkillFoundationMapper.to_domain(model) for model in models]

    def add_many(self, foundations: list[SkillFoundation]) -> None:
        self._session.add_all(
            [SkillFoundationMapper.to_model(foundation) for foundation in foundations]
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(SkillFoundationModel))

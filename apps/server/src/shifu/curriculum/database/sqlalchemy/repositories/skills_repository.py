from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.entities import Skill
from shifu.curriculum.database.sqlalchemy.mappers import SkillMapper
from shifu.curriculum.database.sqlalchemy.models import SkillModel


class SqlalchemySkillsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, skill_id: str) -> Skill | None:
        model = self._session.scalar(
            select(SkillModel).where(SkillModel.id == skill_id)
        )
        return SkillMapper.to_domain(model) if model is not None else None

    def find_many_by_ids(self, skill_ids: tuple[str, ...]) -> list[Skill]:
        models = self._session.scalars(
            select(SkillModel).where(SkillModel.id.in_(skill_ids))
        ).all()
        return [SkillMapper.to_domain(model) for model in models]

    def find_all(self) -> list[Skill]:
        models = self._session.scalars(
            select(SkillModel).order_by(SkillModel.name)
        ).all()
        return [SkillMapper.to_domain(model) for model in models]

    def search(
        self, *, query: str | None, cursor: str | None, limit: int
    ) -> tuple[list[Skill], str | None]:
        q = select(SkillModel).order_by(SkillModel.name)
        if query:
            q = q.where(SkillModel.name.ilike(f"%{query}%"))
        if cursor:
            q = q.where(SkillModel.name > cursor)
        q = q.limit(limit + 1)
        models = self._session.scalars(q).all()
        next_cursor = None
        if len(models) > limit:
            models = models[:limit]
            next_cursor = models[-1].name
        return [SkillMapper.to_domain(model) for model in models], next_cursor

    def add_many(self, skills: list[Skill]) -> None:
        self._session.add_all([SkillMapper.to_model(skill) for skill in skills])
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(SkillModel))

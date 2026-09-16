from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.entities import Material
from shifu.curriculum.database.sqlalchemy.mappers import MaterialMapper
from shifu.curriculum.database.sqlalchemy.models import MaterialModel


class SqlalchemyMaterialsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, material_id: str) -> Material | None:
        model = self._session.scalar(
            select(MaterialModel).where(MaterialModel.id == material_id)
        )
        return MaterialMapper.to_domain(model) if model is not None else None

    def find_many_by_ids(self, material_ids: tuple[str, ...]) -> list[Material]:
        models = self._session.scalars(
            select(MaterialModel).where(MaterialModel.id.in_(material_ids))
        ).all()
        return [MaterialMapper.to_domain(model) for model in models]

    def find_many_by_skill_id(self, skill_id: str) -> list[Material]:
        models = self._session.scalars(
            select(MaterialModel)
            .where(MaterialModel.skill_id == skill_id)
            .order_by(MaterialModel.title)
        ).all()
        return [MaterialMapper.to_domain(model) for model in models]

    def add_many(self, materials: list[Material]) -> None:
        self._session.add_all(
            [MaterialMapper.to_model(material) for material in materials]
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(MaterialModel))

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.database.sqlalchemy.mappers import CompetencyProgressMapper
from shifu.learning.database.sqlalchemy.models import CompetencyProgressModel


class SqlalchemyCompetencyProgressesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, competency_progress_id: str) -> CompetencyProgress | None:
        model = self._session.scalar(
            select(CompetencyProgressModel).where(
                CompetencyProgressModel.id == competency_progress_id
            )
        )
        return CompetencyProgressMapper.to_domain(model) if model is not None else None

    def find_by_skill_experience_id_and_competency_id(
        self,
        skill_experience_id: str,
        competency_id: str,
    ) -> CompetencyProgress | None:
        model = self._session.scalar(
            select(CompetencyProgressModel).where(
                CompetencyProgressModel.skill_experience_id == skill_experience_id,
                CompetencyProgressModel.competency_id == competency_id,
            )
        )
        return CompetencyProgressMapper.to_domain(model) if model is not None else None

    def find_many_by_skill_experience_id(
        self,
        skill_experience_id: str,
    ) -> list[CompetencyProgress]:
        models = self._session.scalars(
            select(CompetencyProgressModel).where(
                CompetencyProgressModel.skill_experience_id == skill_experience_id
            )
        ).all()
        return [CompetencyProgressMapper.to_domain(model) for model in models]

    def add(self, competency_progress: CompetencyProgress) -> None:
        self._session.add(CompetencyProgressMapper.to_model(competency_progress))

    def add_many(self, competency_progresses: list[CompetencyProgress]) -> None:
        self._session.add_all(
            [
                CompetencyProgressMapper.to_model(progress)
                for progress in competency_progresses
            ]
        )
        self._session.flush()

    def replace(self, competency_progress: CompetencyProgress) -> None:
        self._session.merge(CompetencyProgressMapper.to_model(competency_progress))

    def remove_all(self) -> None:
        self._session.execute(delete(CompetencyProgressModel))

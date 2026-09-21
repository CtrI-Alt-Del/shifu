from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.curriculum.core.domain.structures import CurriculumSequence
from shifu.curriculum.database.sqlalchemy.mappers import CurriculumSequenceMapper
from shifu.curriculum.database.sqlalchemy.models import CurriculumSequenceModel


class SqlalchemyCurriculumSequencesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_competency_id(
        self,
        competency_id: str,
    ) -> CurriculumSequence | None:
        model = self._session.scalar(
            select(CurriculumSequenceModel).where(
                CurriculumSequenceModel.competency_id == competency_id
            )
        )
        return CurriculumSequenceMapper.to_domain(model) if model is not None else None

    def add_many(self, sequences: list[CurriculumSequence]) -> None:
        self._session.add_all(
            [CurriculumSequenceMapper.to_model(sequence) for sequence in sequences]
        )
        self._session.flush()

    def remove_all(self) -> None:
        self._session.execute(delete(CurriculumSequenceModel))

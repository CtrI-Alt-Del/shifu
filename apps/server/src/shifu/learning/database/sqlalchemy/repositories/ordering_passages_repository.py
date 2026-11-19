from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities.ordering_passage import OrderingPassage
from shifu.learning.database.sqlalchemy.mappers import OrderingPassageMapper
from shifu.learning.database.sqlalchemy.models import OrderingPassageModel


class SqlalchemyOrderingPassagesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_active(
        self,
        skill_experience_id: str,
        activity_id: str,
    ) -> OrderingPassage | None:
        model = self._session.scalar(
            select(OrderingPassageModel).where(
                OrderingPassageModel.skill_experience_id == skill_experience_id,
                OrderingPassageModel.activity_id == activity_id,
                OrderingPassageModel.status == 'active',
            )
        )
        return OrderingPassageMapper.to_domain(model) if model is not None else None

    def find_by_key(
        self,
        skill_experience_id: str,
        activity_id: str,
        passage_key: str,
    ) -> OrderingPassage | None:
        model = self._session.scalar(
            select(OrderingPassageModel).where(
                OrderingPassageModel.skill_experience_id == skill_experience_id,
                OrderingPassageModel.activity_id == activity_id,
                OrderingPassageModel.passage_key == passage_key,
            )
        )
        return OrderingPassageMapper.to_domain(model) if model is not None else None

    def add(self, passage: OrderingPassage) -> None:
        self._session.add(OrderingPassageMapper.to_model(passage))

    def update(self, passage: OrderingPassage) -> None:
        model = self._session.get(OrderingPassageModel, passage.id)
        if model is None:
            raise ValueError('Ordering passage does not exist.')
        mapped = OrderingPassageMapper.to_model(passage)
        model.skill_experience_id = mapped.skill_experience_id
        model.activity_id = mapped.activity_id
        model.passage_key = mapped.passage_key
        model.activity_revision = mapped.activity_revision
        model.grading_snapshot = mapped.grading_snapshot
        model.verified_orderings = mapped.verified_orderings
        model.schema_version = mapped.schema_version
        model.status = mapped.status

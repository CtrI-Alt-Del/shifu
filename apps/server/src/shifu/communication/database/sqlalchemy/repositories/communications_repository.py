from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import CommunicationStatus
from shifu.communication.database.sqlalchemy.mappers import CommunicationMapper
from shifu.communication.database.sqlalchemy.models import CommunicationModel


class SqlalchemyCommunicationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, communication_id: str) -> Communication | None:
        model = self._session.scalar(
            select(CommunicationModel).where(CommunicationModel.id == communication_id)
        )
        return CommunicationMapper.to_domain(model) if model is not None else None

    def find_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Communication | None:
        model = self._session.scalar(
            select(CommunicationModel).where(
                CommunicationModel.idempotency_key == idempotency_key
            )
        )
        return CommunicationMapper.to_domain(model) if model is not None else None

    def find_pending_due(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[Communication]:
        models = self._session.scalars(
            select(CommunicationModel)
            .where(
                CommunicationModel.status == CommunicationStatus.PENDING.value,
                or_(
                    CommunicationModel.next_attempt_at.is_(None),
                    CommunicationModel.next_attempt_at <= now,
                ),
            )
            .order_by(CommunicationModel.created_at)
            .limit(limit)
        ).all()
        return [CommunicationMapper.to_domain(model) for model in models]

    def add(self, communication: Communication) -> None:
        self._session.add(CommunicationMapper.to_model(communication))

    def add_many(self, communications: list[Communication]) -> None:
        self._session.add_all(
            [
                CommunicationMapper.to_model(communication)
                for communication in communications
            ]
        )
        self._session.flush()

    def update(self, communication: Communication) -> None:
        self._session.merge(CommunicationMapper.to_model(communication))

    def remove_all(self) -> None:
        self._session.execute(delete(CommunicationModel))

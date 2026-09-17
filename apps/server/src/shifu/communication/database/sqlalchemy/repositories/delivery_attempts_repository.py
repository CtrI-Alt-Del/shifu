from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import DeliveryAttempt
from shifu.communication.database.sqlalchemy.mappers import DeliveryAttemptMapper
from shifu.communication.database.sqlalchemy.models import DeliveryAttemptModel


class SqlalchemyDeliveryAttemptsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_communication_id_and_attempt_number(
        self,
        communication_id: str,
        attempt_number: int,
    ) -> DeliveryAttempt | None:
        model = self._session.scalar(
            select(DeliveryAttemptModel).where(
                DeliveryAttemptModel.communication_id == communication_id,
                DeliveryAttemptModel.attempt_number == attempt_number,
            )
        )
        return DeliveryAttemptMapper.to_domain(model) if model is not None else None

    def add(self, attempt: DeliveryAttempt) -> None:
        self._session.add(DeliveryAttemptMapper.to_model(attempt))

    def add_many(self, attempts: list[DeliveryAttempt]) -> None:
        self._session.add_all(
            [DeliveryAttemptMapper.to_model(attempt) for attempt in attempts]
        )
        self._session.flush()

    def update(self, attempt: DeliveryAttempt) -> None:
        self._session.merge(DeliveryAttemptMapper.to_model(attempt))

    def remove_all(self) -> None:
        self._session.execute(delete(DeliveryAttemptModel))

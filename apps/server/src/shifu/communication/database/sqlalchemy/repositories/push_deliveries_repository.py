from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import PushDelivery
from shifu.communication.database.sqlalchemy.mappers import PushDeliveryMapper
from shifu.communication.database.sqlalchemy.models import PushDeliveryModel


class SqlalchemyPushDeliveriesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many_by_reminder_id(self, reminder_id: str) -> tuple[PushDelivery, ...]:
        models = self._session.scalars(
            select(PushDeliveryModel)
            .where(PushDeliveryModel.reminder_id == reminder_id)
            .order_by(PushDeliveryModel.attempted_at, PushDeliveryModel.id)
            .execution_options(populate_existing=True)
        )
        return tuple(PushDeliveryMapper.to_domain(model) for model in models)

    def try_add(self, delivery: PushDelivery) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(PushDeliveryMapper.to_model(delivery))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def update(self, delivery: PushDelivery) -> None:
        self._session.merge(PushDeliveryMapper.to_model(delivery))
        self._session.flush()

    def remove(self, delivery: PushDelivery) -> None:
        self._session.execute(
            delete(PushDeliveryModel).where(PushDeliveryModel.id == delivery.id)
        )

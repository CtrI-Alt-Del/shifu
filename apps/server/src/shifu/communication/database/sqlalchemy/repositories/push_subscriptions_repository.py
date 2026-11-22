from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import PushSubscription
from shifu.communication.database.sqlalchemy.mappers import PushSubscriptionMapper
from shifu.communication.database.sqlalchemy.models import PushSubscriptionModel


class SqlalchemyPushSubscriptionsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        model = self._session.scalar(
            select(PushSubscriptionModel)
            .where(PushSubscriptionModel.endpoint == endpoint)
            .with_for_update()
        )
        return PushSubscriptionMapper.to_domain(model) if model is not None else None

    def find_many_by_account_id(self, account_id: str) -> tuple[PushSubscription, ...]:
        models = self._session.scalars(
            select(PushSubscriptionModel)
            .where(PushSubscriptionModel.account_id == account_id)
            .order_by(PushSubscriptionModel.created_at, PushSubscriptionModel.id)
        )
        return tuple(PushSubscriptionMapper.to_domain(model) for model in models)

    def add(self, subscription: PushSubscription) -> None:
        self._session.add(PushSubscriptionMapper.to_model(subscription))
        self._session.flush()

    def try_add(self, subscription: PushSubscription) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(PushSubscriptionMapper.to_model(subscription))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def update(self, subscription: PushSubscription) -> None:
        self._session.merge(PushSubscriptionMapper.to_model(subscription))
        self._session.flush()

    def remove(self, subscription: PushSubscription) -> None:
        self._session.execute(
            delete(PushSubscriptionModel).where(
                PushSubscriptionModel.id == subscription.id
            )
        )

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(PushSubscriptionModel).where(
                PushSubscriptionModel.account_id == account_id
            )
        )

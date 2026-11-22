from shifu.communication.core.domain.entities import PushSubscription
from shifu.communication.database.sqlalchemy.models import PushSubscriptionModel


class PushSubscriptionMapper:
    @staticmethod
    def to_domain(model: PushSubscriptionModel) -> PushSubscription:
        return PushSubscription(
            id=model.id,
            account_id=model.account_id,
            endpoint=model.endpoint,
            p256dh_key=model.p256dh_key,
            auth_secret=model.auth_secret,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(subscription: PushSubscription) -> PushSubscriptionModel:
        return PushSubscriptionModel(
            id=subscription.id,
            account_id=subscription.account_id,
            endpoint=subscription.endpoint,
            p256dh_key=subscription.p256dh_key,
            auth_secret=subscription.auth_secret,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

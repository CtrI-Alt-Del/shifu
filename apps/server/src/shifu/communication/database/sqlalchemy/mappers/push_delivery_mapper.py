from shifu.communication.core.domain.entities import PushDelivery
from shifu.communication.core.domain.enums import PushDeliveryStatus
from shifu.communication.database.sqlalchemy.models import PushDeliveryModel


class PushDeliveryMapper:
    @staticmethod
    def to_domain(model: PushDeliveryModel) -> PushDelivery:
        return PushDelivery(
            id=model.id,
            reminder_id=model.reminder_id,
            subscription_id=model.subscription_id,
            status=PushDeliveryStatus(model.status),
            attempted_at=model.attempted_at,
            completed_at=model.completed_at,
            failure_code=model.failure_code,
        )

    @staticmethod
    def to_model(delivery: PushDelivery) -> PushDeliveryModel:
        return PushDeliveryModel(
            id=delivery.id,
            reminder_id=delivery.reminder_id,
            subscription_id=delivery.subscription_id,
            status=delivery.status.value,
            attempted_at=delivery.attempted_at,
            completed_at=delivery.completed_at,
            failure_code=delivery.failure_code,
        )

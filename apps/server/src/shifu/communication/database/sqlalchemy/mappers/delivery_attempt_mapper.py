from shifu.communication.core.domain.entities import DeliveryAttempt
from shifu.communication.core.domain.enums import DeliveryAttemptStatus
from shifu.communication.database.sqlalchemy.models import DeliveryAttemptModel


class DeliveryAttemptMapper:
    @staticmethod
    def to_domain(model: DeliveryAttemptModel) -> DeliveryAttempt:
        return DeliveryAttempt(
            id=model.id,
            communication_id=model.communication_id,
            attempt_number=model.attempt_number,
            status=DeliveryAttemptStatus(model.status),
            attempted_at=model.attempted_at,
            completed_at=model.completed_at,
            provider_message_id=model.provider_message_id,
            failure_code=model.failure_code,
        )

    @staticmethod
    def to_model(attempt: DeliveryAttempt) -> DeliveryAttemptModel:
        return DeliveryAttemptModel(
            id=attempt.id,
            communication_id=attempt.communication_id,
            attempt_number=attempt.attempt_number,
            status=attempt.status.value,
            attempted_at=attempt.attempted_at,
            completed_at=attempt.completed_at,
            provider_message_id=attempt.provider_message_id,
            failure_code=attempt.failure_code,
        )

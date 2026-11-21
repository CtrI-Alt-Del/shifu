from datetime import UTC, datetime
from typing import ClassVar

from shifu.communication.core.domain.entities import PushDelivery
from shifu.communication.core.domain.enums import PushDeliveryStatus
from shifu.fakers.shared.id_provider_faker import IdProviderFaker


class PushDeliveryFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        reminder_id: str | None = None,
        subscription_id: str | None = None,
        status: PushDeliveryStatus = PushDeliveryStatus.SENDING,
        attempted_at: datetime | None = None,
        completed_at: datetime | None = None,
        failure_code: str | None = None,
    ) -> PushDelivery:
        return PushDelivery(
            id=id if id is not None else cls._id_provider.generate(),
            reminder_id=(
                reminder_id if reminder_id is not None else cls._id_provider.generate()
            ),
            subscription_id=(
                subscription_id
                if subscription_id is not None
                else cls._id_provider.generate()
            ),
            status=status,
            attempted_at=attempted_at or datetime.now(UTC),
            completed_at=completed_at,
            failure_code=failure_code,
        )

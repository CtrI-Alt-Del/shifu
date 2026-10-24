from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    ConfirmationDeliveryQueueStatus,
)
from shifu.identity.core.interfaces import (
    ConfirmationDeliveryGateway,
    ConfirmationDeliveryRequest,
    IdentityDatabase,
)
from shifu.shared.core.interfaces import ClockProvider


class QueueConfirmationDeliveryUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        delivery_gateway: ConfirmationDeliveryGateway,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._delivery_gateway = delivery_gateway

    def execute(self, request: ConfirmationDeliveryRequest) -> None:
        result = self._delivery_gateway.queue(request)
        if result.status is not ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE:
            return

        recorded_at = self._clock_provider.now()
        with self._identity_database.transaction() as repositories:
            token_repository = repositories.account_action_tokens
            token = token_repository.find_by_id(request.identity_action_token_id)
            if token is None:
                return

            if token.record_delivery_status(
                AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
                recorded_at,
            ):
                token_repository.update(token)

from typing import cast

from shifu.identity.core.domain.enums import AccountConfirmationDeliveryStatus
from shifu.identity.core.interfaces import (
    ConfirmationAccountActionTokensRepository,
    IdentityDatabase,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.interfaces import ClockProvider


class RecordCommunicationDeliveryStateUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider

    def execute(
        self,
        communication_id: str,
        identity_confirmation_id: str,
        state: AccountConfirmationDeliveryStatus | str,
    ) -> bool:
        try:
            normalized_state = AccountConfirmationDeliveryStatus(state)
        except ValueError:
            raise ValidationError from None

        with self._identity_database.transaction() as repositories:
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            confirmation_token = token_repository.find_by_id(identity_confirmation_id)
            if confirmation_token is None:
                return False
            if confirmation_token.communication_id != communication_id:
                return False

            if not confirmation_token.record_delivery_status(
                normalized_state,
                self._clock_provider.now(),
            ):
                return False
            token_repository.update(confirmation_token)
            return True

from typing import cast

from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationAccountActionTokensRepository,
    IdentityDatabase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider


class IssuePendingConfirmationContextUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        pending_confirmation_handle_provider: ActionTokenProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._pending_confirmation_handle_provider = (
            pending_confirmation_handle_provider
        )

    def execute(self, account_id: str) -> str:
        pending_handle = self._pending_confirmation_handle_provider.generate()
        pending_handle_hash = self._pending_confirmation_handle_provider.hash(
            pending_handle
        )
        now = self._clock_provider.now()

        with self._identity_database.transaction() as repositories:
            account = repositories.accounts.find_by_id(account_id)
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            confirmation_token = token_repository.find_latest_by_account_id_and_type(
                account_id,
                AccountActionTokenType.EMAIL_CONFIRMATION,
            )
            if (
                account is None
                or account.status is not AccountStatus.PENDING_CONFIRMATION
                or confirmation_token is None
                or confirmation_token.status is not AccountActionTokenStatus.PENDING
            ):
                raise ServiceUnavailableError
            confirmation_token.replace_pending_handle_hash(pending_handle_hash, now)
            token_repository.update(confirmation_token)

        return pending_handle

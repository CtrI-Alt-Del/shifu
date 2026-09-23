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


class VerifyPendingConfirmationContextUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        pending_confirmation_handle_provider: ActionTokenProvider,
    ) -> None:
        self._identity_database = identity_database
        self._pending_confirmation_handle_provider = (
            pending_confirmation_handle_provider
        )

    def execute(self, pending_handle: str, account_id: str) -> bool:
        pending_handle_hash = self._pending_confirmation_handle_provider.hash(
            pending_handle
        )

        with self._identity_database.transaction() as repositories:
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            confirmation_token = token_repository.find_by_pending_handle_hash(
                pending_handle_hash
            )
            account = repositories.accounts.find_by_id(account_id)
            return (
                confirmation_token is not None
                and confirmation_token.account_id == account_id
                and confirmation_token.type is AccountActionTokenType.EMAIL_CONFIRMATION
                and confirmation_token.status is AccountActionTokenStatus.USED
                and account is not None
                and account.status is AccountStatus.ACTIVE
            )

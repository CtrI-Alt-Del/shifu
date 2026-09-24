from datetime import datetime
from typing import cast

from shifu.identity.core.domain.entities import Account, AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationCancellationReason,
    AccountConfirmationResultStatus,
    AccountStatus,
)
from shifu.identity.core.domain.events import (
    AccountActivatedEvent,
    AccountActivatedPayload,
    AccountConfirmationCancelledEvent,
    AccountConfirmationCancelledPayload,
)
from shifu.identity.core.domain.structures import (
    AccountConfirmationResult,
    AccountProfile,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationAccountActionTokensRepository,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.interfaces import ClockProvider


class ConfirmAccountUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
        action_token_provider: ActionTokenProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider
        self._action_token_provider = action_token_provider

    def execute(self, token: str) -> AccountConfirmationResult:
        token_hash = self._action_token_provider.hash(token)
        confirmed_at = self._clock_provider.now()

        with self._identity_database.transaction() as repositories:
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            confirmation_token = token_repository.find_by_hash(token_hash)
            if confirmation_token is None:
                return AccountConfirmationResult(
                    result=AccountConfirmationResultStatus.INVALID
                )

            non_pending_result = self._get_non_pending_result(confirmation_token)
            if non_pending_result is not None:
                return non_pending_result

            account = repositories.accounts.find_by_id(confirmation_token.account_id)
            if (
                account is None
                or account.status is not AccountStatus.PENDING_CONFIRMATION
            ):
                return AccountConfirmationResult(
                    result=AccountConfirmationResultStatus.INVALID
                )

            if confirmed_at >= confirmation_token.expires_at:
                confirmation_token.expire(confirmed_at)
                token_repository.update(confirmation_token)
                return AccountConfirmationResult(
                    result=AccountConfirmationResultStatus.EXPIRED
                )

            return self._activate_account(
                repositories,
                account,
                confirmation_token,
                confirmed_at,
            )

    @staticmethod
    def _get_non_pending_result(
        confirmation_token: AccountActionToken,
    ) -> AccountConfirmationResult | None:
        if confirmation_token.type is not AccountActionTokenType.EMAIL_CONFIRMATION:
            return AccountConfirmationResult(
                result=AccountConfirmationResultStatus.INVALID
            )
        results = {
            AccountActionTokenStatus.USED: AccountConfirmationResultStatus.USED,
            AccountActionTokenStatus.INVALIDATED: (
                AccountConfirmationResultStatus.INVALID
            ),
            AccountActionTokenStatus.EXPIRED: AccountConfirmationResultStatus.EXPIRED,
        }
        result = results.get(confirmation_token.status)
        return AccountConfirmationResult(result=result) if result is not None else None

    @classmethod
    def _activate_account(
        cls,
        repositories: IdentityDatabaseRepositories,
        account: Account,
        confirmation_token: AccountActionToken,
        confirmed_at: datetime,
    ) -> AccountConfirmationResult:
        confirmation_token.use(confirmed_at)
        account.confirm(confirmed_at)
        repositories.accounts.update(account)
        token_repository = cast(
            'ConfirmationAccountActionTokensRepository',
            repositories.account_action_tokens,
        )
        token_repository.update(confirmation_token)

        all_confirmation_tokens = token_repository.find_many_by_account_id_and_type(
            account.id,
            AccountActionTokenType.EMAIL_CONFIRMATION,
        )
        seen_token_ids = {confirmation_token.id}
        cls._add_cancellation_event(repositories, confirmation_token)
        for sibling_token in all_confirmation_tokens:
            if sibling_token.id in seen_token_ids:
                continue
            seen_token_ids.add(sibling_token.id)
            if sibling_token.status is AccountActionTokenStatus.PENDING:
                sibling_token.invalidate(confirmed_at)
                token_repository.update(sibling_token)
            cls._add_cancellation_event(repositories, sibling_token)

        repositories.events.add(
            AccountActivatedEvent(
                payload=AccountActivatedPayload(
                    account_id=account.id,
                    activated_at=confirmed_at.isoformat(),
                )
            )
        )
        return AccountConfirmationResult(
            result=AccountConfirmationResultStatus.ACTIVATED,
            profile=AccountProfile(
                account_id=account.id,
                display_name=account.display_name,
                email=account.email,
                time_zone=account.time_zone,
                status=account.status,
                created_at=account.created_at,
                confirmed_at=account.confirmed_at,
            ),
            access_version=account.access_version,
        )

    @staticmethod
    def _add_cancellation_event(
        repositories: IdentityDatabaseRepositories,
        confirmation_token: AccountActionToken,
    ) -> None:
        if confirmation_token.communication_id is None:
            return
        repositories.events.add(
            AccountConfirmationCancelledEvent(
                payload=AccountConfirmationCancelledPayload(
                    communication_id=confirmation_token.communication_id,
                    identity_confirmation_id=confirmation_token.id,
                    reason=AccountConfirmationCancellationReason.CONFIRMED,
                )
            )
        )
